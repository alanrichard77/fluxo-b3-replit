
from flask import Flask, render_template, request
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
from datetime import datetime
import io, base64, unicodedata
import matplotlib.ticker as mticker

app = Flask(__name__)

def normalize_colname(col):
    col = str(col)
    return ''.join(c for c in unicodedata.normalize('NFD', col)
                   if unicodedata.category(c) != 'Mn').lower().replace(' ', '').replace('.', '')

def parse_valor(valor):
    v = str(valor).replace('r$', '').replace(' ', '').replace('.', '').replace(',', '.').strip().lower()
    if 'mi' in v: return float(v.replace('mi', '')) / 1000
    if 'bi' in v: return float(v.replace('bi', ''))
    if v in ['', '-', 'nan']: return 0.0
    return float(v)

def gerar_grafico():
    df = pd.read_csv("https://raw.githubusercontent.com/alanrichard5/dados/main/fluxo-b3.csv")
    df.columns = [normalize_colname(c) for c in df.columns]
    df['data'] = pd.to_datetime(df['data'], errors='coerce', dayfirst=True)

    for col in ['estrangeiro', 'institucional', 'pessoa_fisica', 'if']:
        df[col] = df[col].apply(parse_valor)
    df['ibov'] = df['ibov'].apply(lambda x: float(str(x).replace('.', '').replace(',', '.')))

    df['estrangeiro_acum'] = df['estrangeiro'].cumsum()
    df['institucional_acum'] = df['institucional'].cumsum()
    df['pessoa_fisica_acum'] = df['pessoa_fisica'].cumsum()
    df['if_acum'] = df['if'].cumsum()

    # Resumo mês a mês
    df['mes'] = df['data'].dt.to_period('M').astype(str)
    resumo_mensal = {}
    for mes, grupo in df.groupby('mes'):
        totais = {
            'Estrangeiro': grupo['estrangeiro'].sum(),
            'Institucional': grupo['institucional'].sum(),
            'Pessoa Física': grupo['pessoa_fisica'].sum(),
            'IF': grupo['if'].sum()
        }
        maior_entrada = max(totais, key=lambda k: totais[k])
        maior_saida = min(totais, key=lambda k: totais[k])
        resumo_mensal[mes] = {
            'maior_entrada': maior_entrada,
            'maior_saida': maior_saida
        }

    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax2 = ax1.twinx()
    ax1.plot(df['data'], df['estrangeiro_acum'], label='Estrangeiro', linewidth=2)
    ax1.plot(df['data'], df['institucional_acum'], label='Institucional', linewidth=2)
    ax1.plot(df['data'], df['pessoa_fisica_acum'], label='Pessoa Física', linewidth=2)
    ax1.plot(df['data'], df['if_acum'], label='IF', linewidth=2)
    ax2.plot(df['data'], df['ibov'], linestyle='--', color='white', label='Ibovespa', alpha=0.4)

    ax1.set_ylabel('Fluxo Acumulado (R$ Bi)')
    ax2.set_ylabel('Ibovespa')
    ax1.grid(True, linestyle='--', alpha=0.3)
    ax1.legend(loc='upper left')
    ax2.legend(loc='upper right')
    ax1.xaxis.set_major_locator(plt.MaxNLocator(6))
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{int(x):,}'.replace(',', '.')))

    plt.tight_layout()
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
    buffer.seek(0)
    imagem = base64.b64encode(buffer.read()).decode()
    plt.close()

    resumo = {
        'estrangeiro_acum': df['estrangeiro_acum'].iloc[-1],
        'institucional_acum': df['institucional_acum'].iloc[-1],
        'pessoa_fisica_acum': df['pessoa_fisica_acum'].iloc[-1],
        'if_acum': df['if_acum'].iloc[-1]
    }
    last_date = df['data'].max().strftime('%d/%m/%Y')
    return imagem, resumo, resumo_mensal, last_date

@app.route('/', methods=['GET', 'POST'])
def home():
    imagem, resumo, resumo_mensal, last_date = gerar_grafico()
    return render_template('home.html', imagem=imagem, resumo=resumo, resumo_mensal=resumo_mensal, last_date=last_date)

if __name__ == '__main__':
    app.run(debug=True)
