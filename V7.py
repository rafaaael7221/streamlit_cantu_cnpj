import time
import os
import pandas as pd
import requests

#Apenas mostra o endereço da receita e indica se é revenda

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
            time.sleep(1) # Respeitando o limite de requisições da API
            
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
            
            # --- CAPTURA DO ENDEREÇO DA RECEITA ---
            tipo_via = limpar_texto(dados_receita.get('tipo_logradouro', ''))
            nome_via = limpar_texto(dados_receita.get('logradouro', ''))
            
            # Força a junção do tipo de logradouro se ele vier preenchido isoladamente
            logradouro_rec = f"{tipo_via} {nome_via}".strip() if tipo_via and tipo_via not in nome_via else nome_via
            numero_rec = limpar_texto(dados_receita.get('numero', ''))
            complemento_rec = limpar_texto(dados_receita.get('complemento', ''))
            cidade_rec = limpar_texto(dados_receita.get('municipio', ''))
            estado_rec = limpar_texto(dados_receita.get('uf', ''))
            cep_rec = limpar_numeros(dados_receita.get('cep', ''))
            
            # Regras de Negócio do Backoffice (Apenas para CNPJ Revenda por enquanto)
            acao_back = ""
            pendencia = ""
            resolucao = ""
            
            if cnae_revenda_identificado:
                print(f"🚨 CLASSIFICAÇÃO: CNPJ REVENDA ({cnae_revenda_identificado})")
                acao_back = "Cancelar Pedido - CNPJ revenda"
                pendencia = "CNPJ Revenda"
                resolucao = "Abrir ticket em massa"
            else:
                print("📋 CLASSIFICAÇÃO: CNPJ Comum (Não é revenda)")

            # Mostra o endereço cadastrado oficialmente
            print(f"\n--- ENDEREÇO CADASTRADO NA RECEITA ---")
            print(f"• Logradouro:  '{logradouro_rec}'")
            print(f"• Número:      '{numero_rec}'" + (f" | Complemento: '{complemento_rec}'" if complemento_rec else ""))
            print(f"• Cidade/UF:   '{cidade_rec}/{estado_rec}'")
            print(f"• CEP:         '{cep_rec}'")
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