from flask import Flask, request, jsonify, render_template
import requests
import geocoder
from datetime import datetime
from servidor_db import salvar_dados
import pandas as pd

app = Flask(__name__)


def calcular_risco_seca(dados):
    pontuacao = 0

    # 1. Precipitação
    if dados['PRECTOTCORR'] < 2:
        pontuacao += 2  # Alto risco
    elif 2 <= dados['PRECTOTCORR'] <= 5:
        pontuacao += 1  # Risco moderado

    # 2. Temperatura Máxima
    if dados['T2M_MAX'] > 35:
        pontuacao += 2  # Alto risco
    elif 25 <= dados['T2M_MAX'] <= 35:
        pontuacao += 1  # Risco moderado

    # 3. Umidade Específica
    if dados['QV2M'] < 4:
        pontuacao += 2  # Alto risco
    elif 4 <= dados['QV2M'] <= 8:
        pontuacao += 1  # Risco moderado

    # 4. Velocidade do Vento a 10 metros
    if dados['WS10M'] > 6:
        pontuacao += 2  # Alto risco
    elif 3 <= dados['WS10M'] <= 6:
        pontuacao += 1  # Risco moderado

    # 5. Pressão Superficial
    if dados['PS'] > 102:
        pontuacao += 2  # Alto risco
    elif 101.3 <= dados['PS'] <= 102:
        pontuacao += 1  # Risco moderado

    # Determinar o nível de risco
    if pontuacao >= 8:
        return 'Alto risco de seca'
    elif pontuacao >= 4:
        return 'Risco moderado de seca'
    else:
        return 'Baixo risco de seca'


def recommend_crop(dados_climaticos, data):
    melhor_cultivo = None
    melhor_pontuacao = float('-inf')  # Inicia com o menor valor possível

    for index, row in data.iterrows():
        # Acesse os requisitos da cultura
        temperature = row['Temperature']
        humidity = row['Humidity']
        rainfall = row['Rainfall']
        crop = row['Crop']
        
        # Calcular a pontuação para a cultura com base nos dados climáticos
        pontuacao = 0
        if dados_climaticos['T2M_MAX'] <= temperature:
            pontuacao += 1  # Boa temperatura
        if dados_climaticos['QV2M'] <= humidity:
            pontuacao += 1  # Boa umidade
        if dados_climaticos['PRECTOTCORR'] >= rainfall:
            pontuacao += 1  # Boa precipitação
        
        # Se a pontuação é melhor que a anterior, atualize a melhor cultura
        if pontuacao > melhor_pontuacao:
            melhor_pontuacao = pontuacao
            melhor_cultivo = crop

    return melhor_cultivo

def calcular_medias(dados_climaticos):
    medias = {}
    parametros = ['T2M_MAX', 'QV2M', 'WS10M', 'PRECTOTCORR', 'PS']
    
    for parametro in parametros:
        valores = list(dados_climaticos.get(parametro, {}).values())
        if valores:
            medias[parametro] = sum(valores) / len(valores)
        else:
            medias[parametro] = None 

    return medias


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Geolocalização e manipulação das datas...
        g = geocoder.ip('me')
        latitude = g.latlng[0] if g.latlng else None
        longitude = g.latlng[1] if g.latlng else None

        start_date = request.form.get('start_date', type=str)
        end_date = request.form.get('end_date', type=str)

        try:
            start_date_obj = datetime.strptime(start_date, '%m/%d/%Y')
            end_date_obj = datetime.strptime(end_date, '%m/%d/%Y')
            start_date = start_date_obj.strftime('%Y%d%m')
            end_date = end_date_obj.strftime('%Y%d%m')
            
            
        except ValueError:
            return jsonify({"error": "As datas devem estar no formato MM/DD/YYYY."}), 400

        if not all([latitude, longitude, start_date, end_date]):
            return jsonify({"error": "Não foi possível obter a localização ou as datas."}), 400

        # URL da NASA POWER API
        parametros = 'T2M_MIN,T2M_MAX,WS10M,PRECTOTCORR,PS,QV2M'
        url = f"https://power.larc.nasa.gov/api/temporal/daily/point?start={start_date}&end={end_date}&latitude={latitude}&longitude={longitude}&community=ag&parameters={parametros}&format=JSON"

        try:
            # Fazer a requisição para a API
            response = requests.get(url)
            response.raise_for_status()
            dados_climaticos = response.json().get('properties', {}).get('parameter', {})

            if not dados_climaticos:
                return jsonify({"error": "Dados climáticos não encontrados."}), 404
            print(dados_climaticos)
            # Calcular médias dos dados diários
            medias = calcular_medias(dados_climaticos)

            if not medias:
                return jsonify({"error": "Dados insuficientes para calcular o risco de seca."}), 400

            # Calcular o risco de seca
            risco = calcular_risco_seca(medias)
            
            # Salvar os dados no banco de dados
            salvar_dados(latitude, longitude, start_date, end_date, medias, risco)

            dados_csv = pd.read_csv('static/dados/Crop_Recommendation.csv')
            
            # Recomendar a melhor cultura
            melhor_cultivo = recommend_crop(medias, dados_csv)

            return render_template('index.html', risco=risco, melhor_cultivo=melhor_cultivo)


        except requests.RequestException as error:
            return jsonify({"error": f"Erro ao acessar a API NASA POWER: {error}"}), 500

    return render_template('index.html', risco=None)


if __name__ == '__main__':
    app.run(debug=True)
