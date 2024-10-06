import sqlite3

# Função para criar o banco de dados e a tabela
def init_db():
    conn = sqlite3.connect('risco_seca.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS riscos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            prectotcorr REAL NOT NULL,
            t2m_max REAL NOT NULL,
            qv2m REAL NOT NULL,
            ws10m REAL NOT NULL,
            indice_uv REAL NOT NULL,
            risco TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()  

def salvar_dados(latitude, longitude, start_date, end_date, dados, risco):
    conn = sqlite3.connect('risco_seca.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO riscos (latitude, longitude, start_date, end_date, prectotcorr, t2m_max, qv2m, ws10m, indice_uv, risco)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (latitude, longitude, start_date, end_date,
          dados['PRECTOTCORR'], dados['T2M_MAX'], dados['QV2M'],
          dados['WS10M'], dados['ALLSKY_SFC_UV_INDEX'], risco))
    conn.commit()
    conn.close()

def exibir_dados():
   
    conn = sqlite3.connect('risco_seca.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM riscos')
    resultados = cursor.fetchall()
    
    conn.close()

    return resultados 