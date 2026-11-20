import re
import csv
import unicodedata
from typing import List, Dict, Optional, Tuple

try:
    from rapidfuzz import process, fuzz
    HAS_RAPIDFUZZ = True
except ImportError:
    import difflib
    HAS_RAPIDFUZZ = False

NODE_REGISTRY = {
    "INTERCAMBIADOR_SANTA_CRUZ": {
        "name": "Intercambiador Santa Cruz",
        "municipality": "Santa Cruz de Tenerife",
        "lat": 28.4583,
        "lon": -16.2575,
        "is_hub": True,
        "aliases": ["SANTA CRUZ", "INTERCAMBIADOR SANTA CRUZ", "INTERCAMBIADOR SC", "SC", "INTERCAMBIADOR"]
    },
    "INTERCAMBIADOR_LA_LAGUNA": {
        "name": "Intercambiador La Laguna",
        "municipality": "San Cristóbal de La Laguna",
        "lat": 28.4842,
        "lon": -16.3150,
        "is_hub": True,
        "aliases": ["LA LAGUNA", "INTERCAMBIADOR LAGUNA", "LAGUNA", "INTERCAMBIADOR LA LAGUNA", "TRINIDAD"]
    },
    "AEROPUERTO_SUR_TFS": {
        "name": "Aeropuerto Reina Sofía (TFS)",
        "municipality": "Granadilla de Abona",
        "lat": 28.0445,
        "lon": -16.5725,
        "is_hub": True,
        "aliases": ["AEROPUERTO DEL SUR TFS", "AEROPUERTO SUR", "AEROPUERTO DEL SUR", "AEROPUERTOS SUR", "TFS", "AEROPUERTO REINA SOFIA"]
    },
    "AEROPUERTO_NORTE_TFN": {
        "name": "Aeropuerto Tenerife Norte (TFN)",
        "municipality": "San Cristóbal de La Laguna",
        "lat": 28.4827,
        "lon": -16.3415,
        "is_hub": True,
        "aliases": ["AEROPUERTO NORTE", "AEROPUERTOS NORTE", "AEROPUERTO DEL NORTE", "LOS RODEOS", "TFN"]
    },
    "ESTACION_COSTA_ADEJE": {
        "name": "Estación Costa Adeje",
        "municipality": "Adeje",
        "lat": 28.0725,
        "lon": -16.7297,
        "is_hub": True,
        "aliases": ["COSTA ADEJE", "ESTACION COSTA ADEJE", "ESTACION ADEJE", "ADEJE"]
    },
    "LOS_CRISTIANOS": {
        "name": "Los Cristianos",
        "municipality": "Arona",
        "lat": 28.0531,
        "lon": -16.7164,
        "is_hub": True,
        "aliases": ["LOS CRISTIANOS", "ESTACION LOS CRISTIANOS", "CRISTIANOS"]
    },
    "PUERTO_DE_LA_CRUZ": {
        "name": "Puerto de la Cruz",
        "municipality": "Puerto de la Cruz",
        "lat": 28.4150,
        "lon": -16.5492,
        "is_hub": True,
        "aliases": ["PUERTO DE LA CRUZ", "ESTACION PUERTO DE LA CRUZ", "PUERTO CRUZ", "PUERTO"]
    },
    "ICOD_DE_LOS_VINOS": {
        "name": "Icod de los Vinos",
        "municipality": "Icod de los Vinos",
        "lat": 28.3686,
        "lon": -16.7119,
        "is_hub": True,
        "aliases": ["ICOD DE LOS VINOS", "ICOD", "ESTACION DE ICOD", "ESTACION ICOD"]
    },
    "LA_OROTAVA": {
        "name": "La Orotava",
        "municipality": "La Orotava",
        "lat": 28.3917,
        "lon": -16.5239,
        "is_hub": True,
        "aliases": ["LA OROTAVA", "OROTAVA", "ESTACION DE LA OROTAVA", "ESTACION LA OROTAVA", "ESTACION OROTAVA"]
    },
    "LOS_REALEJOS": {
        "name": "Los Realejos",
        "municipality": "Los Realejos",
        "lat": 28.3847,
        "lon": -16.5828,
        "is_hub": False,
        "aliases": ["LOS REALEJOS", "ENLACE LOS REALEJOS", "REALEJOS", "REALEJO ALTO", "REALEJO BAJO"]
    },
    "TACORONTE": {
        "name": "Tacoronte",
        "municipality": "Tacoronte",
        "lat": 28.4800,
        "lon": -16.4128,
        "is_hub": False,
        "aliases": ["TACORONTE", "EL CALVARIO DE TACORONTE", "ZONA CENTRO DE TACORONTE", "EL CALVARIO"]
    },
    "EL_SAUZAL": {
        "name": "El Sauzal",
        "municipality": "El Sauzal",
        "lat": 28.4764,
        "lon": -16.4356,
        "is_hub": False,
        "aliases": ["EL SAUZAL", "ALTOS DEL SAUZAL", "SAUZAL"]
    },
    "CANDELARIA": {
        "name": "Candelaria",
        "municipality": "Candelaria",
        "lat": 28.3547,
        "lon": -16.3719,
        "is_hub": False,
        "aliases": ["CANDELARIA"]
    },
    "GUIMAR": {
        "name": "Güímar",
        "municipality": "Güímar",
        "lat": 28.3144,
        "lon": -16.4111,
        "is_hub": False,
        "aliases": ["GUIMAR", "GUÍMAR", "GÜIMAR", "GÜÍMAR", "ENLACE GUIMAR", "ENLACE GÜÍMAR", "PUERTITO DE GUIMAR", "PUERTITO DE GÜIMAR"]
    },
    "SAN_ISIDRO": {
        "name": "San Isidro",
        "municipality": "Granadilla de Abona",
        "lat": 28.0767,
        "lon": -16.5583,
        "is_hub": True,
        "aliases": ["SAN ISIDRO"]
    },
    "GRANADILLA": {
        "name": "Granadilla",
        "municipality": "Granadilla de Abona",
        "lat": 28.1250,
        "lon": -16.5764,
        "is_hub": False,
        "aliases": ["GRANADILLA", "GRANADILLA DE ABONA", "INSTITUTO GRANADILLA"]
    },
    "EL_MEDANO": {
        "name": "El Médano",
        "municipality": "Granadilla de Abona",
        "lat": 28.0456,
        "lon": -16.5367,
        "is_hub": False,
        "aliases": ["EL MEDANO", "EL MÉDANO", "MEDANO"]
    },
    "SAN_MIGUEL": {
        "name": "San Miguel",
        "municipality": "San Miguel de Abona",
        "lat": 28.0983,
        "lon": -16.6167,
        "is_hub": False,
        "aliases": ["SAN MIGUEL", "SAN MIGUEL DE ABONA", "EL ROQUE GRANADILLA"]
    },
    "ARONA": {
        "name": "Arona",
        "municipality": "Arona",
        "lat": 28.0994,
        "lon": -16.6806,
        "is_hub": False,
        "aliases": ["ARONA", "LA SABINITA"]
    },
    "VILAFLOR": {
        "name": "Vilaflor",
        "municipality": "Vilaflor",
        "lat": 28.1583,
        "lon": -16.6361,
        "is_hub": False,
        "aliases": ["VILAFLOR", "LA ESCALONA"]
    },
    "SANTIAGO_DEL_TEIDE": {
        "name": "Santiago del Teide",
        "municipality": "Santiago del Teide",
        "lat": 28.2958,
        "lon": -16.8164,
        "is_hub": False,
        "aliases": ["SANTIAGO DEL TEIDE", "VALLE SANTIAGO", "ARGUAYO"]
    },
    "GUIA_DE_ISORA": {
        "name": "Guía de Isora",
        "municipality": "Guía de Isora",
        "lat": 28.2114,
        "lon": -16.7797,
        "is_hub": False,
        "aliases": ["GUIA DE ISORA", "GUÍA DE ISORA", "GUIA ISORA", "ESTACION GUIA DE ISORA", "CHIGUERGUE"]
    },
    "LOS_GIGANTES": {
        "name": "Los Gigantes",
        "municipality": "Santiago del Teide",
        "lat": 28.2417,
        "lon": -16.8417,
        "is_hub": False,
        "aliases": ["LOS GIGANTES", "ACANTILADOS DE LOS GIGANTES"]
    },
    "BUENAVISTA_DEL_NORTE": {
        "name": "Buenavista del Norte",
        "municipality": "Buenavista del Norte",
        "lat": 28.3689,
        "lon": -16.8519,
        "is_hub": False,
        "aliases": ["BUENAVISTA", "BUENAVISTA DEL NORTE", "EL PALMAR", "LAS PORTELAS"]
    },
    "MASCA": {
        "name": "Masca",
        "municipality": "Buenavista del Norte",
        "lat": 28.3056,
        "lon": -16.8400,
        "is_hub": False,
        "aliases": ["MASCA"]
    },
    "PUNTA_DE_TENO": {
        "name": "Punta de Teno",
        "municipality": "Buenavista del Norte",
        "lat": 28.3417,
        "lon": -16.9200,
        "is_hub": False,
        "aliases": ["PUNTA DE TENO", "TENO"]
    },
    "TEGUESTE": {
        "name": "Tegueste",
        "municipality": "Tegueste",
        "lat": 28.5222,
        "lon": -16.3389,
        "is_hub": False,
        "aliases": ["TEGUESTE", "EL SOCORRO"]
    },
    "TEJINA": {
        "name": "Tejina",
        "municipality": "San Cristóbal de La Laguna",
        "lat": 28.5322,
        "lon": -16.3533,
        "is_hub": False,
        "aliases": ["TEJINA", "EL BOQUERON"]
    },
    "BAJAMAR": {
        "name": "Bajamar",
        "municipality": "San Cristóbal de La Laguna",
        "lat": 28.5539,
        "lon": -16.3458,
        "is_hub": False,
        "aliases": ["BAJAMAR"]
    },
    "PUNTA_DEL_HIDALGO": {
        "name": "Punta del Hidalgo",
        "municipality": "San Cristóbal de La Laguna",
        "lat": 28.5683,
        "lon": -16.3267,
        "is_hub": False,
        "aliases": ["PUNTA DEL HIDALGO", "PUNTA HIDALGO"]
    },
    "SAN_ANDRES": {
        "name": "San Andrés",
        "municipality": "Santa Cruz de Tenerife",
        "lat": 28.5028,
        "lon": -16.1917,
        "is_hub": False,
        "aliases": ["SAN ANDRES", "SAN ANDRÉS"]
    },
    "LAS_TERESITAS": {
        "name": "Playa de Las Teresitas",
        "municipality": "Santa Cruz de Tenerife",
        "lat": 28.5089,
        "lon": -16.1856,
        "is_hub": False,
        "aliases": ["PLAYA DE LAS TERESITAS", "LAS TERESITAS", "TERESITAS"]
    },
    "ANAZA": {
        "name": "Añaza",
        "municipality": "Santa Cruz de Tenerife",
        "lat": 28.4319,
        "lon": -16.3056,
        "is_hub": False,
        "aliases": ["ANAZA", "AÑAZA", "CENTROS COMERCIALES"]
    },
    "TACO": {
        "name": "Taco",
        "municipality": "San Cristóbal de La Laguna",
        "lat": 28.4556,
        "lon": -16.3056,
        "is_hub": False,
        "aliases": ["TACO"]
    },
    "LA_CUESTA": {
        "name": "La Cuesta",
        "municipality": "San Cristóbal de La Laguna",
        "lat": 28.4681,
        "lon": -16.2958,
        "is_hub": False,
        "aliases": ["LA CUESTA", "CUESTA"]
    },
    "EL_CARDONAL": {
        "name": "El Cardonal",
        "municipality": "San Cristóbal de La Laguna",
        "lat": 28.4611,
        "lon": -16.3083,
        "is_hub": False,
        "aliases": ["EL CARDONAL", "CARDONAL", "ANDENES"]
    },
    "HOSPITAL_UNIVERSITARIO": {
        "name": "Hospital Universitario (HUC)",
        "municipality": "San Cristóbal de La Laguna",
        "lat": 28.4550,
        "lon": -16.2900,
        "is_hub": False,
        "aliases": ["HOSPITAL UNIVERSITARIO", "HOSPITAL LA CANDELARIA", "HOSPITALES", "HOSPITAL"]
    },
    "CAMPUS_GUAJARA": {
        "name": "Campus Guajara ULL",
        "municipality": "San Cristóbal de La Laguna",
        "lat": 28.4667,
        "lon": -16.3083,
        "is_hub": False,
        "aliases": ["CAMPUS GUAJARA", "CAMPUS DE GUAJARA", "GUAJARA", "UNIVERSIDAD"]
    },
    "EL_PORTILLO": {
        "name": "El Portillo (Parque Nacional del Teide)",
        "municipality": "La Orotava",
        "lat": 28.2989,
        "lon": -16.5658,
        "is_hub": False,
        "aliases": ["EL PORTILLO", "PORTILLO", "CENTRO DE VISTANTES PORTILLO BAJO", "PORTILLO BAJO"]
    },
    "PARADOR_DEL_TEIDE": {
        "name": "Parador del Teide / Teleférico",
        "municipality": "La Orotava",
        "lat": 28.2250,
        "lon": -16.6267,
        "is_hub": False,
        "aliases": ["PARADOR DE TURISMO", "TELEFERICO", "CAÑADAS DEL TEIDE", "CANADAS DEL TEIDE"]
    },
    "CRUZ_DEL_CARMEN": {
        "name": "Cruz del Carmen (Anaga)",
        "municipality": "San Cristóbal de La Laguna",
        "lat": 28.5317,
        "lon": -16.2792,
        "is_hub": False,
        "aliases": ["CRUZ DEL CARMEN"]
    },
    "AFUR": {
        "name": "Afur (Anaga)",
        "municipality": "San Cristóbal de La Laguna",
        "lat": 28.5514,
        "lon": -16.2542,
        "is_hub": False,
        "aliases": ["AFUR"]
    },
    "TAGANANA": {
        "name": "Taganana",
        "municipality": "Santa Cruz de Tenerife",
        "lat": 28.5583,
        "lon": -16.2167,
        "is_hub": False,
        "aliases": ["TAGANANA"]
    },
    "CHAMORGA": {
        "name": "Chamorga",
        "municipality": "Santa Cruz de Tenerife",
        "lat": 28.5750,
        "lon": -16.1583,
        "is_hub": False,
        "aliases": ["CHAMORGA"]
    },
    "EL_BAILADERO": {
        "name": "El Bailadero",
        "municipality": "Santa Cruz de Tenerife",
        "lat": 28.5472,
        "lon": -16.1972,
        "is_hub": False,
        "aliases": ["EL BAILADERO", "BAILADERO"]
    },
    "RADAZUL": {
        "name": "Radazul",
        "municipality": "El Rosario",
        "lat": 28.4028,
        "lon": -16.3250,
        "is_hub": False,
        "aliases": ["RADAZUL", "RADAZUL BAJO"]
    },
    "TABAIBA": {
        "name": "Tabaiba",
        "municipality": "El Rosario",
        "lat": 28.3972,
        "lon": -16.3417,
        "is_hub": False,
        "aliases": ["TABAIBA"]
    },
    "BARRANCO_HONDO": {
        "name": "Barranco Hondo",
        "municipality": "Candelaria",
        "lat": 28.3800,
        "lon": -16.3500,
        "is_hub": False,
        "aliases": ["BARRANCO HONDO"]
    },
    "LAS_CALETILLAS": {
        "name": "Las Caletillas",
        "municipality": "Candelaria",
        "lat": 28.3680,
        "lon": -16.3630,
        "is_hub": False,
        "aliases": ["LAS CALETILLAS", "CALETILLAS"]
    },
    "ARAFO": {
        "name": "Arafo",
        "municipality": "Arafo",
        "lat": 28.3417,
        "lon": -16.4167,
        "is_hub": False,
        "aliases": ["ARAFO"]
    },
    "POLIGONO_GUIMAR": {
        "name": "Polígono de Güímar",
        "municipality": "Arafo",
        "lat": 28.3278,
        "lon": -16.3889,
        "is_hub": False,
        "aliases": ["POLÍGONO DE GÜIMAR", "POLIGONO DE GUIMAR", "POLIGONO DE GUÍMAR"]
    },
    "FASNIA": {
        "name": "Fasnia",
        "municipality": "Fasnia",
        "lat": 28.2417,
        "lon": -16.4417,
        "is_hub": False,
        "aliases": ["FASNIA"]
    },
    "ARICO": {
        "name": "Arico",
        "municipality": "Arico",
        "lat": 28.1889,
        "lon": -16.4889,
        "is_hub": False,
        "aliases": ["ARICO", "EL PORIS", "COSTA DE ARICO", "LAS MARETAS"]
    },
    "EL_TABLADO": {
        "name": "El Tablado",
        "municipality": "Arico",
        "lat": 28.2167,
        "lon": -16.4250,
        "is_hub": False,
        "aliases": ["EL TABLADO", "TABLADO"]
    },
    "LAS_ERAS": {
        "name": "Las Eras",
        "municipality": "Fasnia",
        "lat": 28.2278,
        "lon": -16.4194,
        "is_hub": False,
        "aliases": ["LAS ERAS"]
    },
    "LA_SOMBRERA": {
        "name": "La Sombrera",
        "municipality": "Fasnia",
        "lat": 28.2389,
        "lon": -16.4361,
        "is_hub": False,
        "aliases": ["LA SOMBRERA"]
    },
    "LOS_ROQUES": {
        "name": "Los Roques",
        "municipality": "Fasnia",
        "lat": 28.2000,
        "lon": -16.4333,
        "is_hub": False,
        "aliases": ["LOS ROQUES"]
    },
    "LAS_GALLETAS": {
        "name": "Las Galletas",
        "municipality": "Arona",
        "lat": 28.0097,
        "lon": -16.6583,
        "is_hub": False,
        "aliases": ["LAS GALLETAS", "INSTITUTO LAS GALLETAS"]
    },
    "COSTA_DEL_SILENCIO": {
        "name": "Costa del Silencio",
        "municipality": "Arona",
        "lat": 28.0069,
        "lon": -16.6458,
        "is_hub": False,
        "aliases": ["COSTA DEL SILENCIO", "GUARGACHO", "PALM MAR"]
    },
    "LOS_ABRIGOS": {
        "name": "Los Abrigos",
        "municipality": "Granadilla de Abona",
        "lat": 28.0319,
        "lon": -16.5917,
        "is_hub": False,
        "aliases": ["LOS ABRIGOS"]
    },
    "GOLF_DEL_SUR": {
        "name": "Golf del Sur",
        "municipality": "San Miguel de Abona",
        "lat": 28.0389,
        "lon": -16.6083,
        "is_hub": False,
        "aliases": ["GOLF DEL SUR", "COSTA SAN MIGUEL"]
    },
    "LAS_CHAFIRAS": {
        "name": "Las Chafiras",
        "municipality": "San Miguel de Abona",
        "lat": 28.0611,
        "lon": -16.6028,
        "is_hub": False,
        "aliases": ["LAS CHAFIRAS", "CHAFIRAS", "ALDEA BLANCA", "PARQUE LA REINA", "GUAZA"]
    },
    "EL_FRAILE": {
        "name": "El Fraile",
        "municipality": "Arona",
        "lat": 28.0167,
        "lon": -16.6750,
        "is_hub": False,
        "aliases": ["EL FRAILE"]
    },
    "VALLE_SAN_LORENZO": {
        "name": "Valle San Lorenzo",
        "municipality": "Arona",
        "lat": 28.0833,
        "lon": -16.6583,
        "is_hub": False,
        "aliases": ["VALLE SAN LORENZO"]
    },
    "LA_CAMELLA": {
        "name": "La Camella",
        "municipality": "Arona",
        "lat": 28.0778,
        "lon": -16.6889,
        "is_hub": False,
        "aliases": ["LA CAMELLA"]
    },
    "CABO_BLANCO": {
        "name": "Cabo Blanco",
        "municipality": "Arona",
        "lat": 28.0694,
        "lon": -16.6806,
        "is_hub": False,
        "aliases": ["CABO BLANCO"]
    },
    "CHAYOFA": {
        "name": "Chayofa",
        "municipality": "Arona",
        "lat": 28.0722,
        "lon": -16.7028,
        "is_hub": False,
        "aliases": ["CHAYOFA"]
    },
    "LA_CALETA": {
        "name": "La Caleta",
        "municipality": "Adeje",
        "lat": 28.0972,
        "lon": -16.7528,
        "is_hub": False,
        "aliases": ["LA CALETA"]
    },
    "PLAYA_PARAISO": {
        "name": "Playa Paraíso",
        "municipality": "Adeje",
        "lat": 28.1194,
        "lon": -16.7722,
        "is_hub": False,
        "aliases": ["PLAYA PARAÍSO", "PLAYA PARAISO"]
    },
    "CALLAO_SALVAJE": {
        "name": "Callao Salvaje",
        "municipality": "Adeje",
        "lat": 28.1197,
        "lon": -16.7806,
        "is_hub": False,
        "aliases": ["CALLAO SALVAJE"]
    },
    "SAN_JUAN_DE_LA_RAMBLA": {
        "name": "San Juan de la Rambla",
        "municipality": "San Juan de la Rambla",
        "lat": 28.3944,
        "lon": -16.6472,
        "is_hub": False,
        "aliases": ["SAN JUAN DE LA RAMBLA", "SAN JOSE"]
    },
    "LA_GUANCHA": {
        "name": "La Guancha",
        "municipality": "La Guancha",
        "lat": 28.3722,
        "lon": -16.6528,
        "is_hub": False,
        "aliases": ["LA GUANCHA"]
    },
    "EL_TANQUE": {
        "name": "El Tanque",
        "municipality": "El Tanque",
        "lat": 28.3583,
        "lon": -16.7806,
        "is_hub": False,
        "aliases": ["EL TANQUE"]
    },
    "ERJOS": {
        "name": "Puerto de Erjos",
        "municipality": "Los Silos",
        "lat": 28.3278,
        "lon": -16.8056,
        "is_hub": False,
        "aliases": ["PUERTO DE ERJOS", "ERJOS"]
    },
    "PLAYA_SAN_MARCOS": {
        "name": "Playa San Marcos",
        "municipality": "Icod de los Vinos",
        "lat": 28.3750,
        "lon": -16.7167,
        "is_hub": False,
        "aliases": ["PLAYA SAN MARCOS"]
    },
    "AGUAMANSA": {
        "name": "Aguamansa",
        "municipality": "La Orotava",
        "lat": 28.3611,
        "lon": -16.5028,
        "is_hub": False,
        "aliases": ["AGUAMANSA", "EL VELO"]
    },
    "LA_CALDERA": {
        "name": "La Caldera",
        "municipality": "La Orotava",
        "lat": 28.3472,
        "lon": -16.5167,
        "is_hub": False,
        "aliases": ["LA CALDERA"]
    },
    "LA_GALLEGA": {
        "name": "La Gallega",
        "municipality": "Santa Cruz de Tenerife",
        "lat": 28.4389,
        "lon": -16.3278,
        "is_hub": False,
        "aliases": ["LA GALLEGA"]
    },
    "TINCER": {
        "name": "Tincer",
        "municipality": "Santa Cruz de Tenerife",
        "lat": 28.4444,
        "lon": -16.3194,
        "is_hub": False,
        "aliases": ["TINCER", "LAS HESPERIDES"]
    },
    "BARRANCO_GRANDE": {
        "name": "Barranco Grande",
        "municipality": "Santa Cruz de Tenerife",
        "lat": 28.4389,
        "lon": -16.3111,
        "is_hub": False,
        "aliases": ["BARRANCO GRANDE", "LLANO DEL MORO", "GENETO"]
    },
    "SANTA_MARIA_DEL_MAR": {
        "name": "Santa María del Mar",
        "municipality": "Santa Cruz de Tenerife",
        "lat": 28.4361,
        "lon": -16.2972,
        "is_hub": False,
        "aliases": ["SANTA MARIA DEL MAR", "SANTA MARÍA DEL MAR", "SANTA MARIA", "ALISIOS"]
    },
    "ACORAN": {
        "name": "Acorán",
        "municipality": "Santa Cruz de Tenerife",
        "lat": 28.4194,
        "lon": -16.3083,
        "is_hub": False,
        "aliases": ["ACORAN", "ACORÁN", "COSTANERA", "BOCA CANGREJO"]
    },
    "SAN_MATIAS": {
        "name": "San Matías",
        "municipality": "San Cristóbal de La Laguna",
        "lat": 28.4528,
        "lon": -16.3000,
        "is_hub": False,
        "aliases": ["SAN MATIAS", "SAN MATÍAS", "CHAMBERI", "CHAMBERÍ"]
    },
    "FINCA_ESPANA": {
        "name": "Finca España",
        "municipality": "San Cristóbal de La Laguna",
        "lat": 28.4722,
        "lon": -16.3056,
        "is_hub": False,
        "aliases": ["FINCA ESPAÑA", "FINCA ESPANA"]
    },
    "BARRIO_LA_SALUD": {
        "name": "Barrio de la Salud",
        "municipality": "Santa Cruz de Tenerife",
        "lat": 28.4722,
        "lon": -16.2694,
        "is_hub": False,
        "aliases": ["BARRIO DE LA SALUD", "BARRIO LA SALUD", "BARRIO SALUD", "CUESTA PIEDRA"]
    },
    "OFRA": {
        "name": "Ofra",
        "municipality": "Santa Cruz de Tenerife",
        "lat": 28.4611,
        "lon": -16.2806,
        "is_hub": False,
        "aliases": ["OFRA", "BARRIO DE OFRA", "JUAN XXIII"]
    },
    "PLAZA_WEYLER": {
        "name": "Plaza Weyler",
        "municipality": "Santa Cruz de Tenerife",
        "lat": 28.4681,
        "lon": -16.2556,
        "is_hub": False,
        "aliases": ["PLAZA WEYLER", "CALLE EL PILAR", "PLAZA LOS PATOS", "BARRIO NUEVO", "MIRAFLORES"]
    },
    "PLAZA_DE_ESPANA": {
        "name": "Plaza de España",
        "municipality": "Santa Cruz de Tenerife",
        "lat": 28.4667,
        "lon": -16.2472,
        "is_hub": False,
        "aliases": ["PLAZA DE ESPAÑA", "PLAZA DE ESPANA", "LA MARINA", "MUELLE NORTE"]
    },
    "VALLE_GUERRA": {
        "name": "Valle de Guerra",
        "municipality": "San Cristóbal de La Laguna",
        "lat": 28.5139,
        "lon": -16.3889,
        "is_hub": False,
        "aliases": ["VALLE GUERRA", "VALLE DE GUERRA"]
    },
    "GUAMASA": {
        "name": "Guamasa",
        "municipality": "San Cristóbal de La Laguna",
        "lat": 28.4833,
        "lon": -16.3722,
        "is_hub": False,
        "aliases": ["GUAMASA", "GARIMBA"]
    },
    "LAS_MERCEDES": {
        "name": "Las Mercedes",
        "municipality": "San Cristóbal de La Laguna",
        "lat": 28.5111,
        "lon": -16.3000,
        "is_hub": False,
        "aliases": ["LAS MERCEDES", "LAS CANTERAS", "CRUZ DE LOS ALAMOS"]
    },
    "TABORNO": {
        "name": "Taborno",
        "municipality": "San Cristóbal de La Laguna",
        "lat": 28.5417,
        "lon": -16.2417,
        "is_hub": False,
        "aliases": ["TABORNO", "LAS CARBONERAS"]
    },
    "EL_BATAN": {
        "name": "El Batán",
        "municipality": "San Cristóbal de La Laguna",
        "lat": 28.5444,
        "lon": -16.2806,
        "is_hub": False,
        "aliases": ["EL BATAN", "EL BATÁN"]
    },
    "ALMACIGA": {
        "name": "Almáciga",
        "municipality": "Santa Cruz de Tenerife",
        "lat": 28.5722,
        "lon": -16.1972,
        "is_hub": False,
        "aliases": ["ALMACIGA", "ALMÁCIGA"]
    },
    "IGUESTE_SAN_ANDRES": {
        "name": "Igueste de San Andrés",
        "municipality": "Santa Cruz de Tenerife",
        "lat": 28.5306,
        "lon": -16.1556,
        "is_hub": False,
        "aliases": ["IGUESTE DE SAN ANDRES", "IGUESTE DE SAN ANDRÉS", "IGUESTE"]
    },
    "VALLESECO": {
        "name": "Valleseco",
        "municipality": "Santa Cruz de Tenerife",
        "lat": 28.4889,
        "lon": -16.2306,
        "is_hub": False,
        "aliases": ["VALLESECO", "LA QUEBRADA", "BARRIO DE LA ALEGRIA", "BARRIO DE LA ALEGRÍA"]
    },
    "MARIA_JIMENEZ": {
        "name": "María Jiménez",
        "municipality": "Santa Cruz de Tenerife",
        "lat": 28.4944,
        "lon": -16.2222,
        "is_hub": False,
        "aliases": ["MARIA JIMENEZ", "MARÍA JIMÉMEZ", "MARÍA JIMÉNEZ", "LOS VALLES"]
    },
    "LORO_PARQUE": {
        "name": "Loro Parque",
        "municipality": "Puerto de la Cruz",
        "lat": 28.4083,
        "lon": -16.5639,
        "is_hub": False,
        "aliases": ["LORO PARQUE", "PUNTA BRAVA", "LA LONGUERA"]
    },
    "BOTANICO": {
        "name": "Jardín Botánico",
        "municipality": "Puerto de la Cruz",
        "lat": 28.4111,
        "lon": -16.5333,
        "is_hub": False,
        "aliases": ["BOTANICO", "BOTÁNICO", "DURAZNO"]
    },
    "PLAYA_DEL_SOCORRO": {
        "name": "Playa del Socorro",
        "municipality": "Los Realejos",
        "lat": 28.3972,
        "lon": -16.6028,
        "is_hub": False,
        "aliases": ["PLAYA DEL SOCORRO", "SOCORRO"]
    }
}

ALIAS_LOOKUP = {}
for node_id, data in NODE_REGISTRY.items():
    ALIAS_LOOKUP[node_id] = node_id
    clean_canonical = re.sub(r'[^A-Z0-9]', '', data["name"].upper())
    ALIAS_LOOKUP[clean_canonical] = node_id
    for alias in data.get("aliases", []):
        normalized = re.sub(r'[^A-Z0-9]', '', alias.upper())
        if normalized:
            ALIAS_LOOKUP[normalized] = node_id


def normalize_text(text: str) -> str:
    nfkd_form = unicodedata.normalize('NFKD', text)
    cleaned = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    return cleaned.upper().strip()


def resolve_entity(raw_name: str, threshold: float = 80.0) -> Optional[str]:
    norm = normalize_text(raw_name)
    key = re.sub(r'[^A-Z0-9]', '', norm)
    if key in ALIAS_LOOKUP:
        return ALIAS_LOOKUP[key]

    all_keys = list(ALIAS_LOOKUP.keys())
    if HAS_RAPIDFUZZ:
        match = process.extractOne(key, all_keys, scorer=fuzz.token_sort_ratio)
        if match and match[1] >= threshold:
            return ALIAS_LOOKUP[match[0]]
    else:
        matches = difflib.get_close_matches(key, all_keys, n=1, cutoff=threshold / 100.0)
        if matches:
            return ALIAS_LOOKUP[matches[0]]

    for node_id, data in NODE_REGISTRY.items():
        for alias in data.get("aliases", []):
            alias_norm = normalize_text(alias)
            if alias_norm and alias_norm in norm:
                return node_id

    return None


def parse_line_stops(line_name: str) -> Tuple[List[str], bool]:
    text = normalize_text(line_name)
    text = re.sub(r'^(LINEA\s*\d+\s*[-:]?\s*)', '', text)
    is_circular = "CIRCULAR" in text

    text = re.sub(r'\b(DIRECTA|DIRECTO|SIN PARADAS|NOCTURNA|LANZADERA ULL|LANZADERA)\b', '', text)
    text = text.replace('->', ' - ').replace('–', '-').replace('/', ' - ')

    segments = []
    if " POR " in text:
        parts = text.split(" POR ")
        base = parts[0]
        via_parts = " POR ".join(parts[1:])
        base_stops = [s.strip() for s in re.split(r'[-–]', base) if s.strip()]
        via_stops = [s.strip() for s in re.split(r'[-–]| Y ', via_parts) if s.strip()]
        if len(base_stops) >= 2:
            segments = [base_stops[0]] + via_stops + base_stops[1:]
        elif len(base_stops) == 1:
            segments = [base_stops[0]] + via_stops
        else:
            segments = via_stops
    else:
        if '-' in text:
            segments = [s.strip() for s in text.split('-') if s.strip()]
        else:
            segments = [text]

    extracted_nodes = []
    for seg in segments:
        words = seg.split()
        matched = False
        for window_size in range(len(words), 0, -1):
            for i in range(len(words) - window_size + 1):
                chunk = " ".join(words[i:i + window_size])
                node_id = resolve_entity(chunk)
                if node_id and (not extracted_nodes or extracted_nodes[-1] != node_id):
                    extracted_nodes.append(node_id)
                    matched = True
                    break
            if matched:
                break

    if len(extracted_nodes) < 2:
        found_matches = []
        for node_id, info in NODE_REGISTRY.items():
            for alias in info["aliases"]:
                alias_norm = normalize_text(alias)
                idx = text.find(alias_norm)
                if idx != -1:
                    found_matches.append((idx, len(alias_norm), node_id))
        found_matches.sort(key=lambda x: (x[0], -x[1]))
        reordered = []
        last_end = -1
        for idx, length, node_id in found_matches:
            if idx >= last_end:
                if not reordered or reordered[-1] != node_id:
                    reordered.append(node_id)
                last_end = idx + length
        if len(reordered) >= 2:
            extracted_nodes = reordered

    if is_circular and len(extracted_nodes) >= 2:
        if extracted_nodes[0] != extracted_nodes[-1]:
            extracted_nodes.append(extracted_nodes[0])

    return extracted_nodes, is_circular


def parse_csv_routes(csv_path: str) -> List[Dict]:
    routes = []
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            line_num = row.get("linea_numero", "").strip().zfill(3)
            line_name = row.get("linea_nombre", "").strip()
            line_url = row.get("linea_url", "").strip()
            stops, is_circular = parse_line_stops(line_name)
            if len(stops) >= 2:
                routes.append({
                    "line_number": line_num,
                    "line_name": line_name,
                    "line_url": line_url,
                    "stops": stops,
                    "is_circular": is_circular
                })
    return routes
