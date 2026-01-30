import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pdfplumber
import PyPDF2
import re
import os
from datetime import datetime, timedelta
import warnings
import tempfile
from io import BytesIO
import base64
import json
warnings.filterwarnings('ignore')

# ============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ============================================================================
st.set_page_config(
    page_title="FINANALYTICS - Análise Inteligente de Balanços",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="📊"
)

# CSS personalizado
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
        padding: 0px 20px;
    }
    
    h1, h2, h3, h4 {
        color: #ffffff;
        font-family: 'Inter', sans-serif;
    }
    
    /* Cards métricas */
    .metric-positive {
        background: linear-gradient(135deg, rgba(0, 204, 102, 0.1) 0%, rgba(0, 204, 102, 0.2) 100%);
        border-radius: 12px;
        padding: 20px;
        border-left: 4px solid #00cc66;
        margin: 8px 0;
    }
    
    .metric-negative {
        background: linear-gradient(135deg, rgba(255, 75, 75, 0.1) 0%, rgba(255, 75, 75, 0.2) 100%);
        border-radius: 12px;
        padding: 20px;
        border-left: 4px solid #ff4d4d;
        margin: 8px 0;
    }
    
    .metric-neutral {
        background: linear-gradient(135deg, rgba(255, 204, 0, 0.1) 0%, rgba(255, 204, 0, 0.2) 100%);
        border-radius: 12px;
        padding: 20px;
        border-left: 4px solid #ffcc00;
        margin: 8px 0;
    }
    
    /* Upload area */
    .upload-area {
        border: 2px dashed #00cc66;
        border-radius: 15px;
        padding: 40px;
        text-align: center;
        background-color: rgba(0, 204, 102, 0.05);
        transition: all 0.3s ease;
    }
    
    .upload-area:hover {
        background-color: rgba(0, 204, 102, 0.1);
        border-color: #00ff88;
    }
    
    /* Animações */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .fade-in {
        animation: fadeIn 0.5s ease-out;
    }
    
    /* Status indicators */
    .status-good {
        color: #00ff88;
        font-weight: bold;
    }
    
    .status-warning {
        color: #ffcc00;
        font-weight: bold;
    }
    
    .status-bad {
        color: #ff6b6b;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# 2. TÍTULO E DESCRIÇÃO
# ============================================================================
col_title, col_logo = st.columns([4, 1])
with col_title:
    st.title("📊 FINANALYTICS - Análise Inteligente de Balanços")
    st.markdown("""
    <div style='color: #888; margin-bottom: 30px;'>
    Extraia automaticamente dados financeiros de balanços em PDF, analise indicadores e identifique oportunidades
    </div>
    """, unsafe_allow_html=True)
with col_logo:
    st.markdown("""
    <div style='text-align: center; padding: 20px;'>
        <div style='font-size: 48px;'>💼</div>
        <div style='color: #00cc66; font-weight: bold;'>AI Powered</div>
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# 3. FUNÇÕES DE PROCESSAMENTO DE PDF
# ============================================================================
class PDFAnalyzer:
    def __init__(self):
        self.financial_data = {}
        self.company_info = {}
        self.extracted_tables = []
        
    def extract_text_from_pdf(self, pdf_file):
        """Extrai texto completo do PDF"""
        try:
            text = ""
            with pdfplumber.open(pdf_file) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text
        except Exception as e:
            st.error(f"Erro ao extrair texto: {str(e)}")
            return ""
    
    def extract_tables_from_pdf(self, pdf_file):
        """Extrai tabelas do PDF"""
        tables = []
        try:
            with pdfplumber.open(pdf_file) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_tables = page.extract_tables()
                    if page_tables:
                        for table in page_tables:
                            if table and len(table) > 1:  # Ignorar tabelas vazias
                                df_table = pd.DataFrame(table[1:], columns=table[0])
                                tables.append({
                                    'page': page_num + 1,
                                    'table': df_table
                                })
            return tables
        except Exception as e:
            st.warning(f"Algumas tabelas podem não ter sido extraídas: {str(e)}")
            return []
    
    def identify_company_info(self, text):
        """Identifica informações da empresa no texto"""
        info = {}
        
        # Padrões para identificar nome da empresa
        patterns = {
            'company_name': [
                r'RAZÃO SOCIAL:\s*(.+)',
                r'NOME DA EMPRESA:\s*(.+)',
                r'EMPRESA:\s*(.+)',
                r'^(.*?)\s+CNPJ'
            ],
            'cnpj': [
                r'CNPJ:\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})',
                r'CNPJ\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})'
            ],
            'period': [
                r'EXERCÍCIO SOCIAL\s*(\d{4})',
                r'PERÍODO:\s*(.+\d{4})',
                r'ANO BASE\s*(\d{4})',
                r'(\d{4})\s*-\s*Balanço'
            ],
            'date': [
                r'(\d{2}/\d{2}/\d{4})',
                r'DATA:\s*(\d{2}/\d{2}/\d{4})'
            ]
        }
        
        for key, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    info[key] = match.group(1).strip()
                    break
        
        return info
    
    def extract_financial_data(self, text):
        """Extrai dados financeiros do texto usando regex"""
        financial_data = {}
        
        # Padrões para contas do balanço patrimonial
        balance_sheet_patterns = {
            'ativo_total': [r'ATIVO TOTAL\s*R?\$?\s*([\d.,]+)', r'TOTAL DO ATIVO\s*R?\$?\s*([\d.,]+)'],
            'passivo_total': [r'PASSIVO TOTAL\s*R?\$?\s*([\d.,]+)', r'TOTAL DO PASSIVO\s*R?\$?\s*([\d.,]+)'],
            'patrimonio_liquido': [r'PATRIMÔNIO LÍQUIDO\s*R?\$?\s*([\d.,]+)', r'PL\s*R?\$?\s*([\d.,]+)'],
            'ativo_circulante': [r'ATIVO CIRCULANTE\s*R?\$?\s*([\d.,]+)'],
            'passivo_circulante': [r'PASSIVO CIRCULANTE\s*R?\$?\s*([\d.,]+)'],
            'ativo_nao_circulante': [r'ATIVO NÃO CIRCULANTE\s*R?\$?\s*([\d.,]+)'],
            'passivo_nao_circulante': [r'PASSIVO NÃO CIRCULANTE\s*R?\$?\s*([\d.,]+)'],
            'disponibilidades': [r'DISPONIBILIDADES\s*R?\$?\s*([\d.,]+)', r'CAIXA E EQUIVALENTES\s*R?\$?\s*([\d.,]+)'],
            'estoques': [r'ESTOQUES\s*R?\$?\s*([\d.,]+)'],
            'contas_a_receber': [r'CONTAS A RECEBER\s*R?\$?\s*([\d.,]+)'],
            'imobilizado': [r'IMOBILIZADO\s*R?\$?\s*([\d.,]+)', r'IMOBILIZAÇÃO\s*R?\$?\s*([\d.,]+)'],
        }
        
        # Padrões para DRE
        income_statement_patterns = {
            'receita_operacional_liquida': [r'RECEITA OPERACIONAL LÍQUIDA\s*R?\$?\s*([\d.,]+)', 
                                          r'RECEITA LÍQUIDA\s*R?\$?\s*([\d.,]+)'],
            'custo_mercadorias_vendidas': [r'CUSTO DAS MERCADORIAS VENDIDAS\s*R?\$?\s*([\d.,]+)',
                                         r'CMV\s*R?\$?\s*([\d.,]+)'],
            'lucro_bruto': [r'LUCRO BRUTO\s*R?\$?\s*([\d.,]+)'],
            'despesas_operacionais': [r'DESPESAS OPERACIONAIS\s*R?\$?\s*([\d.,]+)'],
            'lucro_operacional': [r'LUCRO OPERACIONAL\s*R?\$?\s*([\d.,]+)', 
                                r'RESULTADO OPERACIONAL\s*R?\$?\s*([\d.,]+)'],
            'lucro_liquido': [r'LUCRO LÍQUIDO\s*R?\$?\s*([\d.,]+)', 
                            r'RESULTADO LÍQUIDO\s*R?\$?\s*([\d.,]+)'],
            'ebitda': [r'EBITDA\s*R?\$?\s*([\d.,]+)'],
            'ebit': [r'EBIT\s*R?\$?\s*([\d.,]+)'],
        }
        
        # Função auxiliar para extrair valores
        def extract_value(patterns, text):
            for pattern_list in patterns:
                for pattern in pattern_list:
                    match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                    if match:
                        value_str = match.group(1).replace('.', '').replace(',', '.')
                        try:
                            return float(value_str)
                        except:
                            return None
            return None
        
        # Extrair dados do balanço patrimonial
        for key, patterns in balance_sheet_patterns.items():
            value = extract_value([patterns], text)
            if value:
                financial_data[key] = value
        
        # Extrair dados da DRE
        for key, patterns in income_statement_patterns.items():
            value = extract_value([patterns], text)
            if value:
                financial_data[key] = value
        
        # Calcular derivados se tivermos dados suficientes
        if 'ativo_circulante' in financial_data and 'passivo_circulante' in financial_data:
            financial_data['liquidez_corrente'] = (
                financial_data['ativo_circulante'] / financial_data['passivo_circulante']
                if financial_data['passivo_circulante'] != 0 else 0
            )
        
        if 'patrimonio_liquido' in financial_data and 'ativo_total' in financial_data:
            financial_data['pl_sobre_ativo'] = (
                financial_data['patrimonio_liquido'] / financial_data['ativo_total']
                if financial_data['ativo_total'] != 0 else 0
            )
        
        if 'lucro_liquido' in financial_data and 'receita_operacional_liquida' in financial_data:
            financial_data['margem_liquida'] = (
                financial_data['lucro_liquido'] / financial_data['receita_operacional_liquida']
                if financial_data['receita_operacional_liquida'] != 0 else 0
            )
        
        if 'lucro_bruto' in financial_data and 'receita_operacional_liquida' in financial_data:
            financial_data['margem_bruta'] = (
                financial_data['lucro_bruto'] / financial_data['receita_operacional_liquida']
                if financial_data['receita_operacional_liquida'] != 0 else 0
            )
        
        if 'ebit' in financial_data and 'ativo_total' in financial_data:
            financial_data['roa'] = (
                financial_data['ebit'] / financial_data['ativo_total']
                if financial_data['ativo_total'] != 0 else 0
            )
        
        if 'lucro_liquido' in financial_data and 'patrimonio_liquido' in financial_data:
            financial_data['roe'] = (
                financial_data['lucro_liquido'] / financial_data['patrimonio_liquido']
                if financial_data['patrimonio_liquido'] != 0 else 0
            )
        
        return financial_data
    
    def analyze_pdf(self, pdf_file):
        """Processa o PDF e extrai todas as informações"""
        # Extrair texto
        text = self.extract_text_from_pdf(pdf_file)
        
        if not text:
            return None
        
        # Extrair informações da empresa
        company_info = self.identify_company_info(text)
        
        # Extrair dados financeiros
        financial_data = self.extract_financial_data(text)
        
        # Extrair tabelas
        tables = self.extract_tables_from_pdf(pdf_file)
        
        return {
            'company_info': company_info,
            'financial_data': financial_data,
            'tables': tables,
            'raw_text': text[:5000]  # Primeiros 5000 caracteres para exibição
        }

# ============================================================================
# 4. FUNÇÕES DE ANÁLISE FINANCEIRA
# ============================================================================
class FinancialAnalyzer:
    @staticmethod
    def calculate_financial_ratios(data):
        """Calcula todos os índices financeiros"""
        ratios = {}
        
        # Extrair dados
        fd = data.get('financial_data', {})
        
        # Liquidez
        if 'liquidez_corrente' in fd:
            ratios['Liquidez Corrente'] = fd['liquidez_corrente']
        
        if 'ativo_circulante' in fd and 'estoques' in fd and 'passivo_circulante' in fd:
            ratios['Liquidez Seca'] = (
                (fd['ativo_circulante'] - fd.get('estoques', 0)) / fd['passivo_circulante']
                if fd['passivo_circulante'] != 0 else 0
            )
        
        # Endividamento
        if 'passivo_total' in fd and 'patrimonio_liquido' in fd:
            ratios['Endividamento Geral'] = (
                fd['passivo_total'] / (fd['passivo_total'] + fd['patrimonio_liquido'])
                if (fd['passivo_total'] + fd['patrimonio_liquido']) != 0 else 0
            )
        
        if 'passivo_total' in fd and 'ativo_total' in fd:
            ratios['Endividamento Total/Ativo'] = (
                fd['passivo_total'] / fd['ativo_total']
                if fd['ativo_total'] != 0 else 0
            )
        
        # Rentabilidade
        if 'roe' in fd:
            ratios['ROE (%)'] = fd['roe'] * 100
        
        if 'roa' in fd:
            ratios['ROA (%)'] = fd['roa'] * 100
        
        if 'margem_liquida' in fd:
            ratios['Margem Líquida (%)'] = fd['margem_liquida'] * 100
        
        if 'margem_bruta' in fd:
            ratios['Margem Bruta (%)'] = fd['margem_bruta'] * 100
        
        # Eficiência
        if 'receita_operacional_liquida' in fd and 'ativo_total' in fd:
            ratios['Giro do Ativo'] = (
                fd['receita_operacional_liquida'] / fd['ativo_total']
                if fd['ativo_total'] != 0 else 0
            )
        
        return ratios
    
    @staticmethod
    def assess_financial_health(ratios):
        """Avalia a saúde financeira com base nos índices"""
        assessment = {}
        
        # Critérios de avaliação
        criteria = {
            'Liquidez Corrente': {
                'bom': 1.5,
                'regular': 1.0,
                'descricao': 'Capacidade de pagar dívidas de curto prazo'
            },
            'Endividamento Geral': {
                'bom': 0.4,
                'regular': 0.6,
                'descricao': 'Proporção de dívida na estrutura de capital',
                'inverse': True  # Quanto menor, melhor
            },
            'ROE (%)': {
                'bom': 15,
                'regular': 8,
                'descricao': 'Retorno sobre o patrimônio líquido'
            },
            'Margem Líquida (%)': {
                'bom': 10,
                'regular': 5,
                'descricao': 'Lucratividade das operações'
            }
        }
        
        for ratio, value in ratios.items():
            if ratio in criteria:
                crit = criteria[ratio]
                if 'inverse' in crit and crit['inverse']:
                    if value <= crit['bom']:
                        assessment[ratio] = {'status': 'BOM', 'color': 'green'}
                    elif value <= crit['regular']:
                        assessment[ratio] = {'status': 'REGULAR', 'color': 'yellow'}
                    else:
                        assessment[ratio] = {'status': 'ATENÇÃO', 'color': 'red'}
                else:
                    if value >= crit['bom']:
                        assessment[ratio] = {'status': 'BOM', 'color': 'green'}
                    elif value >= crit['regular']:
                        assessment[ratio] = {'status': 'REGULAR', 'color': 'yellow'}
                    else:
                        assessment[ratio] = {'status': 'ATENÇÃO', 'color': 'red'}
                
                assessment[ratio]['valor'] = value
                assessment[ratio]['descricao'] = crit['descricao']
        
        return assessment
    
    @staticmethod
    def generate_insights(data, ratios, assessment):
        """Gera insights inteligentes baseados nos dados"""
        insights = []
        
        fd = data.get('financial_data', {})
        
        # Insight sobre liquidez
        if 'Liquidez Corrente' in ratios:
            lc = ratios['Liquidez Corrente']
            if lc < 1.0:
                insights.append({
                    'tipo': 'ALERTA',
                    'titulo': 'Liquidez Baixa',
                    'descricao': f'A empresa pode ter dificuldades para pagar suas dívidas de curto prazo (Liquidez Corrente: {lc:.2f})',
                    'recomendacao': 'Analisar necessidade de capital de giro e estrutura de dívidas'
                })
            elif lc > 3.0:
                insights.append({
                    'tipo': 'INFO',
                    'titulo': 'Excesso de Liquidez',
                    'descricao': f'A empresa mantém recursos ociosos (Liquidez Corrente: {lc:.2f})',
                    'recomendacao': 'Considerar investir recursos excedentes ou distribuir dividendos'
                })
        
        # Insight sobre endividamento
        if 'Endividamento Geral' in ratios:
            eg = ratios['Endividamento Geral']
            if eg > 0.7:
                insights.append({
                    'tipo': 'ALERTA',
                    'titulo': 'Alto Endividamento',
                    'descricao': f'A empresa está muito alavancada (Endividamento: {eg:.1%})',
                    'recomendacao': 'Reduzir dívidas ou renegociar condições'
                })
        
        # Insight sobre rentabilidade
        if 'ROE (%)' in ratios:
            roe = ratios['ROE (%)']
            if roe > 20:
                insights.append({
                    'tipo': 'POSITIVO',
                    'titulo': 'Alta Rentabilidade',
                    'descricao': f'Excelente retorno sobre o patrimônio (ROE: {roe:.1f}%)',
                    'recomendacao': 'Manter estratégia atual'
                })
            elif roe < 5:
                insights.append({
                    'tipo': 'ALERTA',
                    'titulo': 'Baixa Rentabilidade',
                    'descricao': f'Retorno sobre o patrimônio abaixo do esperado (ROE: {roe:.1f}%)',
                    'recomendacao': 'Revisar eficiência operacional e estrutura de custos'
                })
        
        # Insight sobre margem
        if 'Margem Líquida (%)' in ratios:
            margem = ratios['Margem Líquida (%)']
            if margem < 3:
                insights.append({
                    'tipo': 'ALERTA',
                    'titulo': 'Margem Apertada',
                    'descricao': f'Margem líquida muito baixa ({margem:.1f}%)',
                    'recomendacao': 'Revisar preços, custos e despesas operacionais'
                })
        
        # Insight sobre crescimento (se tivermos múltiplos períodos)
        if 'receita_operacional_liquida' in fd:
            insights.append({
                'tipo': 'INFO',
                'titulo': 'Tamanho das Operações',
                'descricao': f'Receita operacional de R$ {fd["receita_operacional_liquida"]:,.2f}',
                'recomendacao': 'Comparar com concorrentes e mercado'
            })
        
        return insights

# ============================================================================
# 5. INTERFACE PRINCIPAL
# ============================================================================
# Inicializar analisadores
pdf_analyzer = PDFAnalyzer()
financial_analyzer = FinancialAnalyzer()

# Sidebar
st.sidebar.header("📁 Upload de Balanços")

# Upload de múltiplos arquivos
uploaded_files = st.sidebar.file_uploader(
    "Selecione os arquivos PDF",
    type=['pdf'],
    accept_multiple_files=True,
    help="Faça upload dos balanços em formato PDF"
)

st.sidebar.divider()

# Opções de análise
st.sidebar.header("⚙️ Configurações de Análise")

analysis_depth = st.sidebar.selectbox(
    "Profundidade da Análise:",
    ["Básica", "Intermediária", "Avançada"],
    index=1
)

include_ratios = st.sidebar.checkbox("Calcular índices financeiros", value=True)
generate_insights = st.sidebar.checkbox("Gerar insights automáticos", value=True)
compare_companies = st.sidebar.checkbox("Comparar múltiplas empresas", value=False)

st.sidebar.divider()

# Botão de processamento
if st.sidebar.button("🚀 Processar Balanços", type="primary", use_container_width=True):
    st.session_state.process_files = True
else:
    if 'process_files' not in st.session_state:
        st.session_state.process_files = False

# ============================================================================
# 6. PROCESSAMENTO DOS ARQUIVOS
# ============================================================================
if st.session_state.process_files and uploaded_files:
    st.header("📊 Processando Balanços")
    
    all_results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, uploaded_file in enumerate(uploaded_files):
        status_text.text(f"Processando {uploaded_file.name}... ({i+1}/{len(uploaded_files)})")
        
        # Analisar PDF
        result = pdf_analyzer.analyze_pdf(uploaded_file)
        
        if result:
            # Adicionar informações do arquivo
            result['filename'] = uploaded_file.name
            result['file_size'] = uploaded_file.size
            
            # Calcular índices financeiros
            if include_ratios and result['financial_data']:
                result['ratios'] = financial_analyzer.calculate_financial_ratios(result)
                result['assessment'] = financial_analyzer.assess_financial_health(result['ratios'])
                
                if generate_insights:
                    result['insights'] = financial_analyzer.generate_insights(
                        result, result['ratios'], result['assessment']
                    )
            
            all_results.append(result)
        
        progress_bar.progress((i + 1) / len(uploaded_files))
    
    status_text.empty()
    progress_bar.empty()
    
    if all_results:
        st.session_state.analysis_results = all_results
        st.success(f"✅ {len(all_results)} arquivo(s) processado(s) com sucesso!")
    else:
        st.error("❌ Não foi possível processar os arquivos. Verifique o formato dos PDFs.")

# ============================================================================
# 7. VISUALIZAÇÃO DOS RESULTADOS
# ============================================================================
if 'analysis_results' in st.session_state and st.session_state.analysis_results:
    results = st.session_state.analysis_results
    
    # Abas principais
    tab_overview, tab_details, tab_compare, tab_export = st.tabs([
        "📈 Visão Geral", 
        "🔍 Detalhes por Empresa", 
        "⚖️ Comparativo", 
        "📤 Exportar"
    ])
    
    with tab_overview:
        st.header("📈 Panorama Financeiro")
        
        # Métricas agregadas
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_companies = len(results)
            st.metric("Empresas Analisadas", total_companies)
        
        with col2:
            avg_roe = np.mean([r.get('ratios', {}).get('ROE (%)', 0) for r in results if r.get('ratios')])
            st.metric("ROE Médio", f"{avg_roe:.1f}%")
        
        with col3:
            avg_margin = np.mean([r.get('ratios', {}).get('Margem Líquida (%)', 0) for r in results if r.get('ratios')])
            st.metric("Margem Líquida Média", f"{avg_margin:.1f}%")
        
        with col4:
            companies_with_good_liquidity = sum(
                1 for r in results 
                if r.get('assessment', {}).get('Liquidez Corrente', {}).get('status') == 'BOM'
            )
            st.metric("Boa Liquidez", f"{companies_with_good_liquidity}/{total_companies}")
        
        # Gráfico de radar para múltiplas empresas
        if len(results) > 1 and compare_companies:
            st.subheader("📊 Comparativo de Desempenho")
            
            # Selecionar indicadores para comparação
            indicators = ['ROE (%)', 'Margem Líquida (%)', 'Liquidez Corrente', 'Endividamento Geral']
            
            # Preparar dados para o gráfico
            plot_data = []
            for result in results:
                company_name = result['company_info'].get('company_name', result['filename'])
                ratios = result.get('ratios', {})
                
                for indicator in indicators:
                    if indicator in ratios:
                        value = ratios[indicator]
                        # Normalizar valores para escala 0-100
                        if indicator == 'Liquidez Corrente':
                            norm_value = min(value * 20, 100)  # Assume 5 como máximo ideal
                        elif indicator == 'Endividamento Geral':
                            norm_value = 100 - (value * 100)  # Inverso (menor é melhor)
                        else:
                            norm_value = min(value, 100)
                        
                        plot_data.append({
                            'Empresa': company_name[:20],  # Limitar tamanho do nome
                            'Indicador': indicator,
                            'Valor': norm_value,
                            'Valor Original': value
                        })
            
            if plot_data:
                df_plot = pd.DataFrame(plot_data)
                
                # Gráfico de barras comparativo
                fig = px.bar(
                    df_plot,
                    x='Indicador',
                    y='Valor',
                    color='Empresa',
                    barmode='group',
                    title='Comparativo de Indicadores Financeiros',
                    hover_data=['Valor Original']
                )
                
                fig.update_layout(
                    yaxis_title="Pontuação (0-100)",
                    xaxis_title="",
                    height=500
                )
                
                st.plotly_chart(fig, use_container_width=True)
        
        # Insights agregados
        st.subheader("💡 Insights Gerais")
        
        all_insights = []
        for result in results:
            if 'insights' in result:
                for insight in result['insights']:
                    insight['Empresa'] = result['company_info'].get('company_name', result['filename'])
                    all_insights.append(insight)
        
        if all_insights:
            # Agrupar insights por tipo
            insight_types = {}
            for insight in all_insights:
                tipo = insight['tipo']
                if tipo not in insight_types:
                    insight_types[tipo] = []
                insight_types[tipo].append(insight)
            
            # Exibir insights por categoria
            for tipo, insights in insight_types.items():
                with st.expander(f"{tipo} ({len(insights)})", expanded=tipo == 'ALERTA'):
                    for insight in insights[:5]:  # Limitar a 5 por categoria
                        col_ins1, col_ins2 = st.columns([3, 1])
                        with col_ins1:
                            st.markdown(f"**{insight['titulo']}**")
                            st.caption(insight['descricao'])
                        with col_ins2:
                            st.caption(f"*{insight['Empresa']}*")
    
    with tab_details:
        st.header("🔍 Detalhamento por Empresa")
        
        # Seletor de empresa
        company_options = []
        for i, result in enumerate(results):
            company_name = result['company_info'].get('company_name', f"Empresa {i+1}")
            filename = result['filename']
            company_options.append(f"{company_name} ({filename})")
        
        selected_company = st.selectbox(
            "Selecione a empresa para detalhar:",
            options=company_options,
            key="company_selector"
        )
        
        # Encontrar resultado selecionado
        selected_index = company_options.index(selected_company)
        result = results[selected_index]
        
        if result:
            company_name = result['company_info'].get('company_name', result['filename'])
            
            st.subheader(f"🏢 {company_name}")
            
            # Informações básicas
            col_info1, col_info2 = st.columns(2)
            
            with col_info1:
                st.markdown("**📋 Informações da Empresa**")
                for key, value in result['company_info'].items():
                    st.text(f"{key.replace('_', ' ').title()}: {value}")
            
            with col_info2:
                st.markdown("**📊 Dados do Arquivo**")
                st.text(f"Arquivo: {result['filename']}")
                st.text(f"Tamanho: {result['file_size']:,} bytes")
                if 'ratios' in result:
                    st.text(f"Índices calculados: {len(result['ratios'])}")
            
            # Dados financeiros
            if 'financial_data' in result and result['financial_data']:
                st.subheader("💰 Dados Financeiros Extraídos")
                
                # Dividir dados em categorias
                balance_sheet_items = {}
                income_statement_items = {}
                calculated_items = {}
                
                for key, value in result['financial_data'].items():
                    if any(term in key for term in ['ativo', 'passivo', 'patrimonio']):
                        balance_sheet_items[key] = value
                    elif any(term in key for term in ['receita', 'lucro', 'custo', 'despesa', 'ebit']):
                        income_statement_items[key] = value
                    else:
                        calculated_items[key] = value
                
                # Exibir balanço patrimonial
                if balance_sheet_items:
                    with st.expander("📄 Balanço Patrimonial", expanded=True):
                        df_balance = pd.DataFrame(
                            list(balance_sheet_items.items()),
                            columns=['Conta', 'Valor (R$)']
                        )
                        df_balance['Valor (R$)'] = df_balance['Valor (R$)'].apply(
                            lambda x: f"R$ {x:,.2f}" if isinstance(x, (int, float)) else x
                        )
                        st.dataframe(df_balance, use_container_width=True)
                
                # Exibir DRE
                if income_statement_items:
                    with st.expander("📈 Demonstração do Resultado", expanded=True):
                        df_income = pd.DataFrame(
                            list(income_statement_items.items()),
                            columns=['Conta', 'Valor (R$)']
                        )
                        df_income['Valor (R$)'] = df_income['Valor (R$)'].apply(
                            lambda x: f"R$ {x:,.2f}" if isinstance(x, (int, float)) else x
                        )
                        st.dataframe(df_income, use_container_width=True)
                
                # Exibir índices calculados
                if 'ratios' in result:
                    st.subheader("📊 Índices Financeiros")
                    
                    # Dividir índices por categoria
                    liquidity_ratios = {}
                    debt_ratios = {}
                    profitability_ratios = {}
                    efficiency_ratios = {}
                    
                    for key, value in result['ratios'].items():
                        if 'Liquidez' in key:
                            liquidity_ratios[key] = value
                        elif any(term in key for term in ['Endividamento', 'Dívida']):
                            debt_ratios[key] = value
                        elif any(term in key for term in ['ROE', 'ROA', 'Margem', 'Retorno']):
                            profitability_ratios[key] = value
                        else:
                            efficiency_ratios[key] = value
                    
                    # Exibir em colunas
                    col_rat1, col_rat2 = st.columns(2)
                    
                    with col_rat1:
                        if liquidity_ratios:
                            st.markdown("**💧 Indicadores de Liquidez**")
                            for key, value in liquidity_ratios.items():
                                assessment = result['assessment'].get(key, {})
                                status = assessment.get('status', '')
                                color = assessment.get('color', 'white')
                                
                                if 'Liquidez' in key:
                                    formatted_value = f"{value:.2f}"
                                else:
                                    formatted_value = f"{value:.1%}" if value < 1 else f"{value:.1f}"
                                
                                st.markdown(f"{key}: **<span style='color:{color}'>{formatted_value} {status}</span>**", 
                                          unsafe_allow_html=True)
                        
                        if debt_ratios:
                            st.markdown("**📉 Indicadores de Endividamento**")
                            for key, value in debt_ratios.items():
                                assessment = result['assessment'].get(key, {})
                                status = assessment.get('status', '')
                                color = assessment.get('color', 'white')
                                
                                st.markdown(f"{key}: **<span style='color:{color}'>{value:.1%} {status}</span>**", 
                                          unsafe_allow_html=True)
                    
                    with col_rat2:
                        if profitability_ratios:
                            st.markdown("**📈 Indicadores de Rentabilidade**")
                            for key, value in profitability_ratios.items():
                                assessment = result['assessment'].get(key, {})
                                status = assessment.get('status', '')
                                color = assessment.get('color', 'white')
                                
                                if '%' in key:
                                    formatted_value = f"{value:.1f}%"
                                else:
                                    formatted_value = f"{value:.1%}" if value < 1 else f"{value:.1f}"
                                
                                st.markdown(f"{key}: **<span style='color:{color}'>{formatted_value} {status}</span>**", 
                                          unsafe_allow_html=True)
                        
                        if efficiency_ratios:
                            st.markdown("**⚡ Indicadores de Eficiência**")
                            for key, value in efficiency_ratios.items():
                                assessment = result['assessment'].get(key, {})
                                status = assessment.get('status', '')
                                color = assessment.get('color', 'white')
                                
                                st.markdown(f"{key}: **<span style='color:{color}'>{value:.2f} {status}</span>**", 
                                          unsafe_allow_html=True)
                    
                    # Gráfico de saúde financeira
                    st.subheader("🏥 Saúde Financeira")
                    
                    if result['assessment']:
                        assessment_df = pd.DataFrame([
                            {
                                'Indicador': key,
                                'Status': info['status'],
                                'Valor': info['valor'],
                                'Descrição': info.get('descricao', '')
                            }
                            for key, info in result['assessment'].items()
                        ])
                        
                        # Mapear status para cores
                        color_map = {'BOM': '#00cc66', 'REGULAR': '#ffcc00', 'ATENÇÃO': '#ff6b6b'}
                        assessment_df['Cor'] = assessment_df['Status'].map(color_map)
                        
                        # Gráfico de barras
                        fig = px.bar(
                            assessment_df,
                            x='Indicador',
                            y='Valor',
                            color='Status',
                            color_discrete_map=color_map,
                            title='Avaliação dos Indicadores Financeiros',
                            hover_data=['Descrição', 'Valor'],
                            text='Valor'
                        )
                        
                        fig.update_layout(
                            yaxis_title="Valor",
                            xaxis_title="",
                            height=400,
                            showlegend=True
                        )
                        
                        # Formatar valores no gráfico
                        fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                        
                        st.plotly_chart(fig, use_container_width=True)
                
                # Insights específicos
                if 'insights' in result:
                    st.subheader("💡 Insights e Recomendações")
                    
                    for insight in result['insights']:
                        if insight['tipo'] == 'ALERTA':
                            st.warning(f"**{insight['titulo']}**\n\n{insight['descricao']}\n\n*Recomendação:* {insight['recomendacao']}")
                        elif insight['tipo'] == 'POSITIVO':
                            st.success(f"**{insight['titulo']}**\n\n{insight['descricao']}\n\n*Recomendação:* {insight['recomendacao']}")
                        else:
                            st.info(f"**{insight['titulo']}**\n\n{insight['descricao']}\n\n*Recomendação:* {insight['recomendacao']}")
                
                # Tabelas extraídas
                if result['tables']:
                    st.subheader("📋 Tabelas Extraídas do PDF")
                    
                    for i, table_info in enumerate(result['tables'][:3]):  # Limitar a 3 tabelas
                        with st.expander(f"Tabela {i+1} (Página {table_info['page']})", 
                                       expanded=i==0):
                            df_table = table_info['table']
                            st.dataframe(df_table, use_container_width=True)
    
    with tab_compare:
        if len(results) > 1:
            st.header("⚖️ Análise Comparativa")
            
            # Selecionar empresas para comparar
            company_list = []
            for i, result in enumerate(results):
                name = result['company_info'].get('company_name', f"Empresa {i+1}")
                company_list.append({
                    'id': i,
                    'name': name,
                    'filename': result['filename']
                })
            
            selected_companies = st.multiselect(
                "Selecione as empresas para comparar:",
                options=[f"{c['name']} ({c['filename']})" for c in company_list],
                default=[f"{company_list[0]['name']} ({company_list[0]['filename']})",
                        f"{company_list[1]['name']} ({company_list[1]['filename']})"] if len(company_list) > 1 else None
            )
            
            if selected_companies and len(selected_companies) >= 2:
                # Extrair índices das empresas selecionadas
                selected_indices = []
                for selection in selected_companies:
                    for company in company_list:
                        if f"{company['name']} ({company['filename']})" == selection:
                            selected_indices.append(company['id'])
                            break
                
                # Coletar dados para comparação
                comparison_data = []
                
                for idx in selected_indices:
                    result = results[idx]
                    company_name = result['company_info'].get('company_name', result['filename'])
                    
                    if 'ratios' in result:
                        for ratio_name, ratio_value in result['ratios'].items():
                            comparison_data.append({
                                'Empresa': company_name,
                                'Indicador': ratio_name,
                                'Valor': ratio_value
                            })
                
                if comparison_data:
                    df_comparison = pd.DataFrame(comparison_data)
                    
                    # Pivot para formato wide
                    df_pivot = df_comparison.pivot_table(
                        index='Indicador', 
                        columns='Empresa', 
                        values='Valor'
                    ).reset_index()
                    
                    st.dataframe(df_pivot, use_container_width=True)
                    
                    # Gráfico de radar comparativo
                    st.subheader("📊 Comparativo Visual")
                    
                    # Selecionar indicadores para radar
                    radar_indicators = ['ROE (%)', 'Margem Líquida (%)', 'Liquidez Corrente', 
                                      'Endividamento Geral', 'Giro do Ativo']
                    
                    available_indicators = [ind for ind in radar_indicators if ind in df_pivot['Indicador'].values]
                    
                    if available_indicators:
                        # Filtrar dados
                        df_radar = df_pivot[df_pivot['Indicador'].isin(available_indicators)]
                        
                        # Normalizar valores para radar
                        for indicator in available_indicators:
                            row = df_radar[df_radar['Indicador'] == indicator]
                            for company in selected_companies:
                                company_name = company.split(' (')[0]
                                if company_name in df_radar.columns:
                                    value = row[company_name].values[0]
                                    # Normalização específica por indicador
                                    if indicator == 'Liquidez Corrente':
                                        norm_value = min(value * 20, 100)
                                    elif indicator == 'Endividamento Geral':
                                        norm_value = 100 - (value * 100)
                                    elif '%' in indicator:
                                        norm_value = min(value, 100)
                                    else:
                                        norm_value = min(value * 10, 100)
                                    
                                    df_radar.loc[df_radar['Indicador'] == indicator, company_name] = norm_value
                        
                        # Criar gráfico de radar
                        fig = go.Figure()
                        
                        for company in selected_companies:
                            company_name = company.split(' (')[0]
                            if company_name in df_radar.columns:
                                values = df_radar[company_name].tolist()
                                # Fechar o radar
                                values = values + [values[0]]
                                indicators = df_radar['Indicador'].tolist() + [df_radar['Indicador'].tolist()[0]]
                                
                                fig.add_trace(go.Scatterpolar(
                                    r=values,
                                    theta=indicators,
                                    name=company_name,
                                    fill='toself'
                                ))
                        
                        fig.update_layout(
                            polar=dict(
                                radialaxis=dict(
                                    visible=True,
                                    range=[0, 100]
                                )
                            ),
                            showlegend=True,
                            title="Comparativo Radar - Indicadores Financeiros",
                            height=500
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Tabela de avaliação comparativa
                        st.subheader("🏆 Ranking por Indicador")
                        
                        ranking_data = []
                        for idx in selected_indices:
                            result = results[idx]
                            company_name = result['company_info'].get('company_name', result['filename'])
                            
                            if 'assessment' in result:
                                good_count = sum(1 for v in result['assessment'].values() 
                                               if v.get('status') == 'BOM')
                                regular_count = sum(1 for v in result['assessment'].values() 
                                                  if v.get('status') == 'REGULAR')
                                warning_count = sum(1 for v in result['assessment'].values() 
                                                  if v.get('status') == 'ATENÇÃO')
                                
                                ranking_data.append({
                                    'Empresa': company_name,
                                    '✅ BOM': good_count,
                                    '⚠️ REGULAR': regular_count,
                                    '❌ ATENÇÃO': warning_count,
                                    'Pontuação': good_count * 3 + regular_count * 2 + warning_count * 1
                                })
                        
                        if ranking_data:
                            df_ranking = pd.DataFrame(ranking_data)
                            df_ranking = df_ranking.sort_values('Pontuação', ascending=False)
                            
                            st.dataframe(
                                df_ranking.style.background_gradient(subset=['Pontuação'], cmap='Greens'),
                                use_container_width=True
                            )
        else:
            st.info("📝 Faça upload de pelo menos 2 balanços para usar a análise comparativa.")
    
    with tab_export:
        st.header("📤 Exportar Resultados")
        
        # Opções de exportação
        export_format = st.radio(
            "Selecione o formato de exportação:",
            ["CSV", "Excel", "JSON", "Relatório PDF (simulado)"],
            horizontal=True
        )
        
        # Selecionar dados para exportar
        st.subheader("📋 Selecionar Dados para Exportar")
        
        col_exp1, col_exp2, col_exp3 = st.columns(3)
        
        with col_exp1:
            export_financial_data = st.checkbox("Dados Financeiros", value=True)
            export_ratios = st.checkbox("Índices Financeiros", value=True)
        
        with col_exp2:
            export_assessment = st.checkbox("Avaliações", value=True)
            export_insights = st.checkbox("Insights", value=True)
        
        with col_exp3:
            export_tables = st.checkbox("Tabelas Extraídas", value=False)
            export_raw_text = st.checkbox("Texto Bruto", value=False)
        
        # Botão de exportação
        if st.button("📥 Gerar Arquivo de Exportação", type="primary"):
            with st.spinner("Preparando dados para exportação..."):
                
                # Preparar dados consolidados
                export_data = {}
                
                for i, result in enumerate(results):
                    company_name = result['company_info'].get('company_name', f"Empresa_{i+1}")
                    company_key = company_name.replace(' ', '_').replace('.', '')
                    
                    export_data[company_key] = {}
                    
                    if export_financial_data and 'financial_data' in result:
                        export_data[company_key]['financial_data'] = result['financial_data']
                    
                    if export_ratios and 'ratios' in result:
                        export_data[company_key]['ratios'] = result['ratios']
                    
                    if export_assessment and 'assessment' in result:
                        export_data[company_key]['assessment'] = result['assessment']
                    
                    if export_insights and 'insights' in result:
                        export_data[company_key]['insights'] = result['insights']
                
                # Gerar arquivo conforme formato selecionado
                if export_format == "CSV":
                    # Criar CSV consolidado
                    csv_data = []
                    
                    for company_key, data in export_data.items():
                        if 'ratios' in data:
                            for ratio_name, ratio_value in data['ratios'].items():
                                csv_data.append({
                                    'Empresa': company_key,
                                    'Indicador': ratio_name,
                                    'Valor': ratio_value
                                })
                    
                    if csv_data:
                        df_csv = pd.DataFrame(csv_data)
                        csv_string = df_csv.to_csv(index=False, sep=';', decimal=',')
                        
                        st.download_button(
                            label="⬇️ Baixar CSV",
                            data=csv_string,
                            file_name=f"analise_balancos_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                
                elif export_format == "Excel":
                    # Criar Excel com múltiplas abas
                    excel_buffer = BytesIO()
                    
                    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                        # Aba de índices
                        ratios_data = []
                        for company_key, data in export_data.items():
                            if 'ratios' in data:
                                for ratio_name, ratio_value in data['ratios'].items():
                                    ratios_data.append({
                                        'Empresa': company_key,
                                        'Indicador': ratio_name,
                                        'Valor': ratio_value
                                    })
                        
                        if ratios_data:
                            df_ratios = pd.DataFrame(ratios_data)
                            df_pivot = df_ratios.pivot_table(index='Indicador', 
                                                           columns='Empresa', 
                                                           values='Valor')
                            df_pivot.to_excel(writer, sheet_name='Índices')
                        
                        # Aba de avaliações
                        assessment_data = []
                        for company_key, data in export_data.items():
                            if 'assessment' in data:
                                for indicator, info in data['assessment'].items():
                                    assessment_data.append({
                                        'Empresa': company_key,
                                        'Indicador': indicator,
                                        'Valor': info.get('valor', ''),
                                        'Status': info.get('status', ''),
                                        'Descrição': info.get('descricao', '')
                                    })
                        
                        if assessment_data:
                            df_assessment = pd.DataFrame(assessment_data)
                            df_assessment.to_excel(writer, sheet_name='Avaliações', index=False)
                    
                    excel_buffer.seek(0)
                    
                    st.download_button(
                        label="⬇️ Baixar Excel",
                        data=excel_buffer,
                        file_name=f"analise_balancos_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                
                elif export_format == "JSON":
                    json_string = json.dumps(export_data, indent=2, default=str, ensure_ascii=False)
                    
                    st.download_button(
                        label="⬇️ Baixar JSON",
                        data=json_string,
                        file_name=f"analise_balancos_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                        mime="application/json",
                        use_container_width=True
                    )
                
                else:  # Relatório PDF simulado
                    st.info("""
                    **📄 Relatório PDF (Funcionalidade Simulada)**
                    
                    Em uma versão completa, aqui seria gerado um relatório PDF profissional contendo:
                    
                    1. Capa com logotipo e data
                    2. Sumário executivo
                    3. Análise detalhada por empresa
                    4. Gráficos e tabelas
                    5. Insights e recomendações
                    6. Anexos com dados brutos
                    
                    *Para implementar esta funcionalidade, seriam necessárias bibliotecas adicionais como ReportLab ou WeasyPrint.*
                    """)
                    
                    # Gerar um PDF simples como demonstração
                    from reportlab.lib.pagesizes import letter
                    from reportlab.pdfgen import canvas
                    from reportlab.lib.units import inch
                    
                    pdf_buffer = BytesIO()
                    c = canvas.Canvas(pdf_buffer, pagesize=letter)
                    
                    # Adicionar conteúdo básico
                    c.setFont("Helvetica-Bold", 16)
                    c.drawString(1*inch, 10*inch, "Relatório de Análise de Balanços")
                    c.setFont("Helvetica", 12)
                    c.drawString(1*inch, 9.5*inch, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
                    c.drawString(1*inch, 9*inch, f"Empresas analisadas: {len(results)}")
                    
                    c.showPage()
                    c.save()
                    
                    pdf_buffer.seek(0)
                    
                    st.download_button(
                        label="⬇️ Baixar PDF Demo",
                        data=pdf_buffer,
                        file_name=f"relatorio_demo_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
        
        # Visualização de dados brutos
        with st.expander("📄 Visualizar Dados Brutos Extraídos", expanded=False):
            for i, result in enumerate(results):
                company_name = result['company_info'].get('company_name', result['filename'])
                st.markdown(f"**{company_name}**")
                st.text_area("Texto extraído:", result.get('raw_text', 'Não disponível'), 
                           height=200, key=f"raw_text_{i}")

else:
    # Tela inicial - instruções
    st.header("📁 Como Funciona")
    
    col_inst1, col_inst2, col_inst3 = st.columns(3)
    
    with col_inst1:
        st.markdown("""
        <div style='text-align: center; padding: 20px;'>
            <div style='font-size: 48px;'>1️⃣</div>
            <h3>Upload dos PDFs</h3>
            <p>Faça upload dos balanços em formato PDF na barra lateral</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_inst2:
        st.markdown("""
        <div style='text-align: center; padding: 20px;'>
            <div style='font-size: 48px;'>2️⃣</div>
            <h3>Análise Automática</h3>
            <p>O sistema extrai e processa os dados automaticamente</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_inst3:
        st.markdown("""
        <div style='text-align: center; padding: 20px;'>
            <div style='font-size: 48px;'>3️⃣</div>
            <h3>Visualize Resultados</h3>
            <p>Explore insights, gráficos e relatórios detalhados</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Área de upload destacada
    st.markdown("---")
    st.markdown('<div class="upload-area">', unsafe_allow_html=True)
    st.markdown("""
    <h2 style='text-align: center;'>📤 Área de Upload</h2>
    <p style='text-align: center; color: #888;'>
    Faça upload dos balanços em PDF na barra lateral ⬅️
    </p>
    <p style='text-align: center; font-size: 12px; color: #666;'>
    Formatos suportados: PDF de demonstrações financeiras<br>
    Tamanho máximo: 10MB por arquivo
    </p>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Exemplos de análise
    st.markdown("---")
    st.subheader("📊 Exemplos de Análises Geradas")
    
    col_ex1, col_ex2, col_ex3 = st.columns(3)
    
    with col_ex1:
        st.markdown("""
        <div class="metric-positive">
            <h4>📈 Análise de Rentabilidade</h4>
            <p>ROE, ROA, Margens</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_ex2:
        st.markdown("""
        <div class="metric-neutral">
            <h4>💧 Indicadores de Liquidez</h4>
            <p>Liquidez Corrente e Seca</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_ex3:
        st.markdown("""
        <div class="metric-negative">
            <h4>📉 Endividamento</h4>
            <p>Alavancagem e Estrutura</p>
        </div>
        """, unsafe_allow_html=True)

# ============================================================================
# 8. RODAPÉ E INFORMAÇÕES
# ============================================================================
st.divider()

footer_col1, footer_col2, footer_col3 = st.columns(3)

with footer_col1:
    st.caption(f"**FINANALYTICS v1.0** • {datetime.now().strftime('%d/%m/%Y %H:%M')}")

with footer_col2:
    if 'analysis_results' in st.session_state:
        num_files = len(st.session_state.analysis_results)
        st.caption(f"**{num_files} arquivo(s) processado(s)**")

with footer_col3:
    st.caption("⚠️ Análise para fins educacionais")

# Informações de ajuda
with st.expander("❓ Ajuda e Instruções", expanded=False):
    st.markdown("""
    ### 🎯 **Como usar esta ferramenta:**
    
    1. **Faça upload** dos balanços em PDF na barra lateral
    2. **Configure** as opções de análise desejadas
    3. **Clique em "Processar Balanços"** para iniciar a extração
    4. **Explore as abas** para diferentes visualizações
    
    ### 📋 **Formatos de PDF suportados:**
    
    - Balanços patrimoniais
    - Demonstrações de resultados (DRE)
    - Relatórios da CVM (DFP, ITR)
    - Balanços de empresas em geral
    
    ### 🔍 **O que é extraído automaticamente:**
    
    - **Informações da empresa** (nome, CNPJ, período)
    - **Dados do balanço** (ativo, passivo, patrimônio líquido)
    - **Dados da DRE** (receitas, custos, lucros)
    - **Tabelas estruturadas** do PDF
    
    ### 📊 **Análises geradas:**
    
    - **Índices de liquidez** (corrente, seca)
    - **Índices de endividamento** (geral, composição)
    - **Índices de rentabilidade** (ROE, ROA, margens)
    - **Avaliação da saúde financeira**
    - **Insights automáticos e recomendações**
    
    ### ⚠️ **Limitações atuais:**
    
    - A extração depende da qualidade e formato do PDF
    - Alguns layouts complexos podem não ser processados completamente
    - Recomenda-se usar PDFs com texto selecionável (não escaneados)
    - A precisão da extração varia conforme o padrão do relatório
    
    ### 🔧 **Dicas para melhores resultados:**
    
    1. Use PDFs com texto (não imagens escaneadas)
    2. Prefira relatórios no padrão da CVM
    3. Verifique sempre os dados extraídos
    4. Compare múltiplos períodos para análise temporal
    
    ### 📞 **Suporte:**
    
    Em caso de problemas com a extração, verifique:
    - Se o PDF contém texto selecionável
    - Se o formato segue padrões contábeis
    - Se as informações estão claramente rotuladas
    
    *Esta ferramenta utiliza processamento automatizado e pode exigir ajustes manuais em alguns casos.*
    """)

# Botão de limpar análise
if st.button("🗑️ Limpar Análise Atual", type="secondary"):
    for key in ['process_files', 'analysis_results']:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()