import time
import os
import pandas as pd
import requests

#Mostra se é revenda, compara os endereços e cria uma planilha com os resultados


# 1. Configurações de Caminhos e Parâmetros
CAMINHO_PLANILHA_ORIGEM = r"C:/Users/User/Desktop/enviar.xlsx"
CAMINHO_PLANILHA_DESTINO = r"C:/Users/User/Desktop/resultado.xlsx"


CNAES_REVENDA = [
    "4520001", "4520006", "4520007", "4530701", "4530702", 
    "4530703", "4530704", "4530705", "4530706", "4541202", 
    "4541206", "4541207", "4542101"
]

def limpar_texto(texto):
    if pd.isna(texto) or not texto:
        return ""
    return str(texto).strip().upper()

def limpar_numeros(texto):
    if pd.isna(texto) or not texto:
        return ""
    return "".join(filter(str.isdigit, str(texto)))

def extrair_nucleo_logradouro(texto):
    """Remove prefixos comuns (R, RUA, AV, AVENIDA) para comparar apenas o nome da rua"""
    t = limpar_texto(texto)
    prefixos = ["RUA ", "R ", "AVENIDA ", "AV ", "RODOVIA ", "ROD ", "ALAMEDA ", "AL "]
    for pref in prefixos:
        if t.startswith(pref):
            return t[len(pref):].strip()
    return t

try:
    df_origem = pd.read_excel(CAMINHO_PLANILHA_ORIGEM)
    print(f"Planilha carregada! {len(df_origem)} registros encontrados.\n")
    print("="*80)

    novas_linhas = []

    for index, linha in df_origem.iterrows():
        pedido = linha.get('Pedido', 'N/A')
        cnpj_planilha = limpar_numeros(linha.get('CNPJ', ''))
        
        print(f"\n[PROCESSANDO] Pedido: {pedido} | CNPJ: {cnpj_planilha}")
        
        if not cnpj_planilha:
            print("❌ Erro: Linha sem CNPJ preenchido. Pulando...")
            print("-" * 80)
            continue
            
        url_api = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_planilha}"
        
        try:
            resposta = requests.get(url_api)
            time.sleep(1) 
            
            if resposta.status_code != 200:
                print(f"❌ Erro na BrasilAPI (Status {resposta.status_code}) para o CNPJ {cnpj_planilha}")
                print("-" * 80)
                continue
                
            dados_receita = resposta.json()
            
            # Extração de CNAEs e validação de revenda
            cnae_principal = limpar_numeros(dados_receita.get('cnae_fiscal', ''))
            cnaes_empresa = [cnae_principal]
            for cnae_sec in dados_receita.get('cnaes_secundarios', []):
                cnaes_empresa.append(limpar_numeros(cnae_sec.get('codigo', '')))
            
            cnae_revenda_identificado = next((c for c in cnaes_empresa if c in CNAES_REVENDA), None)
            
            # --- TRATAMENTO DOS LOGRADOUROS ---
            tipo_via = limpar_texto(dados_receita.get('tipo_logradouro', ''))
            nome_via = limpar_texto(dados_receita.get('logradouro', ''))
            
            logradouro_rec = f"{tipo_via} {nome_via}".strip() if tipo_via and tipo_via not in nome_via else nome_via
            logradouro_plan = limpar_texto(linha.get('Logradouro', ''))

            nucleo_plan = extrair_nucleo_logradouro(logradouro_plan)
            nucleo_rec = extrair_nucleo_logradouro(logradouro_rec)

            if nucleo_plan and nucleo_rec and (nucleo_plan in nucleo_rec or nucleo_rec in nucleo_plan):
                comp_logradouro = "IGUAL"
            else:
                comp_logradouro = "DIVERGENTE"
            # ----------------------------------

            # Limpeza dos demais campos
            numero_plan = limpar_texto(linha.get('Número', ''))
            cidade_plan = limpar_texto(linha.get('Cidade', ''))
            estado_plan = limpar_texto(linha.get('Estado', ''))
            cep_plan = limpar_numeros(linha.get('CEP', ''))
            
            numero_rec = limpar_texto(dados_receita.get('numero', ''))
            cidade_rec = limpar_texto(dados_receita.get('municipio', ''))
            estado_rec = limpar_texto(dados_receita.get('uf', ''))
            cep_rec = limpar_numeros(dados_receita.get('cep', ''))
            
            # Outras comparações
            comp_numero = "IGUAL" if numero_plan == numero_rec else "DIVERGENTE"
            comp_cidade = "IGUAL" if cidade_plan == cidade_rec else "DIVERGENTE"
            comp_estado = "IGUAL" if estado_plan == estado_rec else "DIVERGENTE"
            comp_cep = "IGUAL" if cep_plan == cep_rec else "DIVERGENTE"

            endereco_divergente = (
                comp_logradouro == "DIVERGENTE" or
                comp_numero == "DIVERGENTE" or
                comp_cidade == "DIVERGENTE" or
                comp_estado == "DIVERGENTE" or
                comp_cep == "DIVERGENTE"
            )

            # Regras de Negócio do Backoffice (Campos vazios se tudo estiver OK)
            acao_back = ""
            pendencia = ""
            resolucao = ""
            
            if cnae_revenda_identificado:
                print(f"🚨 CLASSIFICAÇÃO: CNPJ REVENDA ({cnae_revenda_identificado})")
                acao_back = "Cancelar Pedido - CNPJ revenda"
                pendencia = "CNPJ Revenda"
                resolucao = "Abrir ticket em massa"
            elif endereco_divergente:
                print("⚠️ CLASSIFICAÇÃO: DIVERGÊNCIA DE ENDEREÇO")
                acao_back = "Atualização de Endereço"
                pendencia = "PJ - Endereço divergente do SEFAZ"
                resolucao = "Abrir ticket em massa"
            else:
                print("✅ CLASSIFICAÇÃO: Pedido Regular")
                # Deixa como string vazia para as colunas não serem preenchidas na planilha gerada

            # Print do Comparativo Visual no Terminal
            print(f"\n--- COMPARATIVO DE ENDEREÇO ---")
            print(f"• Logradouro  -> Planilha: '{logradouro_plan}' | Receita: '{logradouro_rec}' | [{comp_logradouro}]")
            print(f"• Número      -> Planilha: '{numero_plan}' | Receita: '{numero_rec}' | [{comp_numero}]")
            print(f"• Cidade/UF   -> Planilha: '{cidade_plan}/{estado_plan}' | Receita: '{cidade_rec}/{estado_rec}'")
            print(f"• CEP         -> Planilha: '{cep_plan}' | Receita: '{cep_rec}' | [{comp_cep}]")
            print("-" * 80)

            novas_linhas.append({
                "Pedido": pedido, 
                "CNPJ": cnpj_planilha, 
                "Ação Back": acao_back,
                "Pendência": pendencia, 
                "Resolução": resolucao
            })

        except Exception as e_api:
            print(f"❌ Falha ao processar requisição da API para o pedido {pedido}: {e_api}")

    if novas_linhas:
        pd.DataFrame(novas_linhas).to_excel(CAMINHO_PLANILHA_DESTINO, index=False)
        print(f"\n🚀 Processo concluído! Planilha gerada com sucesso em:\n{CAMINHO_PLANILHA_DESTINO}")

except Exception as e:
    print(f"❌ Erro geral: {e}")