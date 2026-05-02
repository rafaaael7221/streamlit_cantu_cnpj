import streamlit as st
import requests

# Configuração da Página
st.set_page_config(page_title="Consulta CNPJ - Cantu Store", page_icon="🏢")

CNAES_REVENDA = [
    "4520001", "4520006", "4520007", "4530701", "4530702", 
    "4530703", "4530704", "4530705", "4530706", "4541202", 
    "4541206", "4541207", "4542101"
]

def verificar_revenda(dados):
    principal = str(dados.get('cnae_fiscal', ''))
    secundarias_lista = dados.get('cnaes_secundarios') or dados.get('secundarios') or []
    secundarias = [str(item.get('codigo', '')) for item in secundarias_lista]
    todas = [principal] + secundarias
    return any(c in CNAES_REVENDA for c in todas)

st.title("🏢 Consulta de CNPJ - CantuStore")
st.markdown("---")

cnpj_input = st.text_input("Digite o CNPJ (apenas números):")

if cnpj_input:
    cnpj_limpo = "".join(filter(str.isdigit, cnpj_input))
    if len(cnpj_limpo) == 14:
        with st.spinner('Buscando dados...'):
            url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}"
            response = requests.get(url)
            
            if response.status_code == 200:
                dados = response.json()
                
                # Alerta de Revenda
                if verificar_revenda(dados):
                    st.error("⚠️ **ALERTA: CNPJ IDENTIFICADO COMO REVENDA**")
                else:
                    st.success("✅ CNPJ Regular")

                # Organização em Colunas
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📍 Endereço")
                    tipo = dados.get('descricao_tipo_de_logradouro', '').title()
                    logra = dados.get('logradouro', 'N/A').title()
                    rua = f"{tipo} {logra}".strip() if tipo and tipo not in logra else logra
                    st.write(f"**Rua:** {rua}, {dados.get('numero')}")
                    st.write(f"**Bairro:** {dados.get('bairro', 'N/A').title()}")
                    st.write(f"**Cidade:** {dados.get('municipio', 'N/A').title()}/{dados.get('uf')}")

                with col2:
                    st.subheader("📝 Dados Cadastrais")
                    st.write(f"**Situação:** {dados.get('descricao_situacao_cadastral')}")
                    st.write(f"**CEP:** {dados.get('cep')}")

                st.markdown("---")
                st.subheader("📊 Atividades Econômicas")
                
                # Principal
                cp = str(dados.get('cnae_fiscal', ''))
                aviso_p = " 🔴 [REVENDA]" if cp in CNAES_REVENDA else ""
                st.write(f"**Principal:** {cp} - {dados.get('cnae_fiscal_descricao')}{aviso_p}")
                
                # Secundárias
                sec = dados.get('cnaes_secundarios') or dados.get('secundarios') or []
                if sec:
                    with st.expander("Ver CNAEs Secundários"):
                        for item in sec:
                            cs = str(item.get('codigo', ''))
                            av_s = " 🔴 [REVENDA]" if cs in CNAES_REVENDA else ""
                            st.write(f"- {cs} - {item.get('descricao')}{av_s}")
            else:
                st.warning("CNPJ não encontrado.")
    else:
        st.info("Por favor, digite um CNPJ válido com 14 dígitos.")