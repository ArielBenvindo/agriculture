from flask import Flask, render_template, request, jsonify
import requests
from datetime import datetime,timedelta
import geocoder
import pandas as pd
from servidor_db import salvar_dados,exibir_dados

app = Flask(__name__)

API_KEY = 'f591ca3edde1dd295936d2ab74e8e375'


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

    if dados['ALLSKY_SFC_UV_INDEX'] > 8:
        pontuacao += 2  # Alto risco
    elif 6 <= dados['ALLSKY_SFC_UV_INDEX'] <= 8:
        pontuacao += 1  # Risco moderado
    

    # Determinar o nível de risco
    if pontuacao >= 8:
        return 'Alto'
    elif pontuacao >= 4:
        return 'Moderado'
    else:
        return 'Baixo'


def recommend_crop(dados_climaticos, data):
    melhor_cultivo = None
    melhor_pontuacao = float('-inf') 

    for index, row in data.iterrows():
        
        temperature = row['Temperature']
        humidity = row['Humidity']
        rainfall = row['Rainfall']
        crop = row['Crop']
        
        pontuacao = 0
        if dados_climaticos['T2M_MAX'] <= temperature:
            pontuacao += 1  
        if dados_climaticos['QV2M'] <= humidity:
            pontuacao += 1 
        if dados_climaticos['PRECTOTCORR'] >= rainfall:
            pontuacao += 1  
        
        if pontuacao > melhor_pontuacao:
            melhor_pontuacao = pontuacao
            melhor_cultivo = crop

    return melhor_cultivo



def calcular_medias(dados_climaticos):
    medias = {}
    parametros = ['T2M_MAX', 'QV2M', 'WS10M', 'PRECTOTCORR', 'ALLSKY_SFC_UV_INDEX']
    
    for parametro in parametros:
        valores = list(dados_climaticos.get(parametro, {}).values())
        print(f"Valores para {parametro}: {valores}")  # Print para verificar os valores
        
        # Filtra valores válidos: excluindo -999 e None, e garantindo que sejam numéricos
        valores_validos = [valor for valor in valores if valor != -999 and valor is not None and isinstance(valor, (int, float))]
        print(f"Valores válidos para {parametro}: {valores_validos}")  # Print para verificar valores válidos
        
        if valores_validos:
            medias[parametro] = sum(valores_validos) / len(valores_validos)
            print(f"Média calculada para {parametro}: {medias[parametro]}")  # Print para verificar a média
        else:
            medias[parametro] = 0
            print(f"Sem valores válidos para calcular a média de {parametro}.")  # Print quando não há valores válidos

    return medias



def get_weather(lat, lon):
    """Fetch the current weather data for given latitude and longitude."""
    url = f'https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric'
    response = requests.get(url)
    return response.json() if response.status_code == 200 else None


def get_coordinates(city):
    """Retrieve latitude and longitude for a given city."""
    url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={API_KEY}"
    response = requests.get(url)
    if response.status_code == 200 and response.json():
        data = response.json()[0]
        return data['lat'], data['lon']
    return None, None


def get_city_name(lat, lon):
    """Get city name from latitude and longitude."""
    url = f"http://api.openweathermap.org/geo/1.0/reverse?lat={lat}&lon={lon}&limit=1&appid={API_KEY}"
    response = requests.get(url)
    if response.status_code == 200 and response.json():
        return response.json()[0]['name']
    return None

@app.route('/', methods=['GET', 'POST'])
def home():
    current_date = datetime.now()
    start_date = (current_date - timedelta(days=3)).strftime('%d/%m/%Y')
    end_date = (current_date).strftime('%d/%m/%Y')


    g = geocoder.ip('me')
    latitude = g.latlng[0] if g.latlng else None
    longitude = g.latlng[1] if g.latlng else None


    city = get_city_name(latitude, longitude)
    city_display = city.capitalize() if city else "Cidade Desconhecida"

    if request.method == 'POST':
        city = request.form.get('city')
        start_date = request.form.get('start_date', type=str) or start_date  
        end_date = request.form.get('end_date', type=str) or end_date        

        if city:
            latitude, longitude = get_coordinates(city)
            city_display = city.capitalize()
            if not latitude or not longitude:
                return "Erro: Não foi possível obter as coordenadas da cidade.", 400

    weather_data = get_weather(latitude, longitude)
    temperature = weather_data['main']['temp'] if weather_data else None
    weather_desc = weather_data['weather'][0]['description'].capitalize() if weather_data else None
    sunrise = weather_data['sys']['sunrise'] if weather_data else None
    sunset = weather_data['sys']['sunset'] if weather_data else None
    current_date_str = current_date.strftime("%b %d %Y")
    day_of_week = current_date.strftime("%A")

    if start_date and end_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%d/%m/%Y')
            end_date_obj = datetime.strptime(end_date, '%d/%m/%Y')
            start_date = start_date_obj.strftime('%Y%m%d') 
            end_date = end_date_obj.strftime('%Y%m%d')      
            
            if start_date > end_date:
                return jsonify({"error": "A data de início deve ser anterior à data de término."}), 400
            
        except ValueError:
            return jsonify({"error": "As datas devem estar no formato DD/MM/YYYY."}), 400

        if not all([latitude, longitude, start_date, end_date]):
            return jsonify({"error": "Não foi possível obter a localização ou as datas."}), 400

        parametros = 'T2M_MIN,T2M_MAX,WS10M,PRECTOTCORR,ALLSKY_SFC_UV_INDEX,QV2M'
        url = f"https://power.larc.nasa.gov/api/temporal/daily/point?start={start_date}&end={end_date}&latitude={latitude}&longitude={longitude}&community=ag&parameters={parametros}&format=JSON"

        try:
            response = requests.get(url)
            response.raise_for_status()
            dados_climaticos = response.json().get('properties', {}).get('parameter', {})

            if not dados_climaticos:
                return jsonify({"error": "Dados climáticos não encontrados."}), 404

            medias = calcular_medias(dados_climaticos)

            if not medias:
                return jsonify({"error": "Dados insuficientes para calcular o risco de seca."}), 400

            risco = calcular_risco_seca(medias)

            salvar_dados(latitude, longitude, start_date, end_date, medias, risco)
            
            dados_csv = pd.read_csv('static/dados/Crop_Recommendation.csv')
            melhor_cultivo = recommend_crop(medias, dados_csv)

            umidade = abs(round(medias['QV2M'], 2))                
            precipitacao = abs(round(medias['PRECTOTCORR'], 2))   
            vento = abs(round(medias['WS10M'], 2))                 
            indice_uv = abs(round(medias['ALLSKY_SFC_UV_INDEX'], 2))
            temperatura_dados = abs(round(medias['T2M_MAX'], 2))  

            return render_template('home.html',
                                city=city_display,
                                temperature=temperature,
                                weather_desc=weather_desc,
                                current_date=current_date_str,
                                day_of_week=day_of_week,
                                risco=risco, 
                                melhor_cultivo=melhor_cultivo,
                                sunrise=sunrise,
                                sunset=sunset,
                                umidade=umidade,
                                precipitacao=precipitacao,
                                vento=vento,
                                indice_uv=indice_uv,
                                temperatura_dados=temperatura_dados)

        except requests.RequestException as error:
            return jsonify({"error": f"Erro ao acessar a API NASA POWER: {error}"}), 500

    return render_template('home.html',
                            city=city_display,
                            temperature=temperature,
                            weather_desc=weather_desc,
                            current_date=current_date_str,
                            day_of_week=day_of_week,
                            sunrise=sunrise,
                            sunset=sunset,
                            risco=None, 
                            melhor_cultivo=None)


# @app.route('/condicoes')
# def condicoes():
#     return render_template('condicoes.html')

# @app.route('/precipitacao')
# def precipitacao():
#     return render_template('precipitacao.html')

# @app.route('/indice_uv')
# def indice_uv():
#     return render_template('indice_uv.html')

# @app.route('/vento')
# def vento():
#     return render_template('vento.html')

# @app.route('/umidade')
# def vento():
#     return render_template('umidade.html')
       

if __name__ == '__main__':
    app.run(debug=True)

