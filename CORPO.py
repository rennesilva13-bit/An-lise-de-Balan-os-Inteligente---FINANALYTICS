import streamlit as st
import pandas as pd
import numpy as np
import os
import re
from datetime import datetime
import warnings
from io import BytesIO
import base64
warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================
st.set_page_config(
    page_title="FINANALYTICS - Análise de Balanços",
    layout="wide"
)

st.title("📊 FINANALYTICS - Análise de Balanços Simplificada")

# ============================================================================
# FUNÇÕES DE ANÁLISE (SEM PLOTLY)
# ============================================================================
class SimpleAnalyzer:
    def extract_from_pdf(self, pdf_file):
        """Versão simplificada sem pdfplumber"""
        try:
            import PyPDF2
            text = ""
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            for page_num, page in enumerate(pdf_reader.pages[:3]):  # Apenas 3 páginas
                text += page.extract_text() + "\n"
            
            return text
        except:
            return ""
    
    def find_financial_data(self, text):
        """Encontra dados financeiros"""
        data = {}
        
        # Busca por valores financeiros
        patterns = {
            'ATIVO': r'(ATIVO\s*TOTAL|TOTAL\s*DO\s*ATIVO)[\s:]*R?\$?\s*([\d.,]+)',
            'PASSIVO': r'(PASSIVO\s*TOTAL|TOTAL\s*DO\s*PASSIVO)[\s:]*R?\$?\s*([\d.,]+)',
            'PATRIMONIO': r'(PATRIMÔNIO\s*LÍQUIDO|PL)[\s:]*R?\$?\s*([\d.,]+)',
            'RECEITA': r'(RECEITA\s*LÍQUIDA|RECEITA\s*OPERACIONAL)[\s:]*R?\$?\s*([\d.,]+)',
            'LUCRO': r'(LUCRO\s*LÍQUIDO|RESULTADO\s*LÍQUIDO)[\s:]*R?\$?\s*([\d.,]+)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value = match.group(2).replace('.', '').replace(',', '.')
                    data[key] = float(value)
                except:
                    pass
        
        return data

# ============================================================================
# INTERFACE
# ============================================================================
st.sidebar.header("📁 Upload de PDF")

uploaded_file = st.sidebar.file_uploader(
    "Selecione o balanço em PDF",
    type=['pdf']
)

if uploaded_file:
    analyzer = SimpleAnalyzer()
    
    with st.spinner("Analisando PDF..."):
        text = analyzer.extract_from_pdf(uploaded_file)
        
        if text:
            data = analyzer.find_financial_data(text)
            
            if data:
                st.success("✅ Dados encontrados!")
                
                # Exibir dados
                st.subheader("📋 Dados Financeiros")
                
                for key, value in data.items():
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.write(f"**{key}:**")
                    with col2:
                        st.write(f"R$ {value:,.2f}")
                
                # Cálculos básicos
                if 'ATIVO' in data and 'PASSIVO' in data:
                    st.subheader("📊 Análise")
                    
                    col_a, col_b, col_c = st.columns(3)
                    
                    with col_a:
                        if data['PASSIVO'] > 0:
                            endividamento = data['PASSIVO'] / data['ATIVO']
                            st.metric("Endividamento", f"{endividamento:.1%}")
                    
                    with col_b:
                        if 'PATRIMONIO' in data and data['PATRIMONIO'] > 0 and 'LUCRO' in data:
                            roe = data['LUCRO'] / data['PATRIMONIO']
                            st.metric("ROE", f"{roe:.1%}")
                    
                    with col_c:
                        if 'ATIVO' in data and data['ATIVO'] > 0 and 'LUCRO' in data:
                            roa = data['LUCRO'] / data['ATIVO']
                            st.metric("ROA", f"{roa:.1%}")
                
                # Gráfico simples com st.bar_chart
                st.subheader("📈 Composição")
                
                if 'ATIVO' in data:
                    chart_data = pd.DataFrame({
                        'Categoria': ['Ativo Total', 'Patrimônio', 'Passivo'],
                        'Valor': [
                            data.get('ATIVO', 0),
                            data.get('PATRIMONIO', 0),
                            data.get('PASSIVO', 0)
                        ]
                    })
                    
                    st.bar_chart(chart_data.set_index('Categoria'))
            
            else:
                st.warning("Não foram encontrados dados financeiros no PDF.")
                
                # Mostrar prévia do texto
                with st.expander("Ver texto extraído"):
                    st.text(text[:2000])
        else:
            st.error("Não foi possível extrair texto do PDF.")
else:
    st.info("👈 Faça upload de um balanço em PDF na barra lateral")

st.sidebar.markdown("---")
st.sidebar.info("""
**💡 Dicas:**
- Use PDFs com texto (não escaneados)
- Formato recomendado: Balanço Patrimonial
- Extração funciona melhor com documentos padronizados
""")
