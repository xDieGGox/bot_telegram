import re

def extraer_parametros(frase):
    # Definimos los patrones regex para cada parámetro
    patrones = {
        'cedula': r'\bcedula\s*es\s*(\d+)',
        'nombres': r'\bme\s*llamo\s*([A-Za-z]+)',
        'apellidos': r'\b([A-Z][a-z]+)\s*(\w+)\s*',
        'telefono': r'\b(\d{10,})',
        'correo': r'\bcorreo\s*es\s*([\w.-]+@[a-zA-Z]+\.[a-zA-Z]+)',
        'edad': r'\bedad\s*es\s*(\d+)',
        'altura': r'\baltura\s*de\s*([\d,]+\.\d+)',
        'peso': r'\bpeso\s*es\s*([\d\.]+)',
        'historialfamiliar': r'\bhistorial\s*familiar\s*es\s*(si|no)',
        'entrecomidas': r'\bentre\s*comidas\s*([a-zA-Z]+)',
        'comidascaloricas': r'\bcomidas\s*caloricas\s*(si|no)'
    }
    
    # Inicializamos los valores extraídos
    parametros = {
        'cedula': None,
        'nombres': None,
        'apellidos': None,
        'telefono': None,
        'correo': None,
        'edad': None,
        'altura': None,
        'peso': None,
        'historialfamiliar': None,
        'entrecomidas': None,
        'comidascaloricas': None
    }
    
    # Iteramos sobre los patrones y buscamos en la frase
    for key, patron in patrones.items():
        match = re.search(patron, frase, re.IGNORECASE)
        if match:
            if key == 'altura' or key == 'peso':
                parametros[key] = float(match.group(1).replace(",", "."))
            elif key == 'edad':
                parametros[key] = int(match.group(1))
            elif key == 'historialfamiliar':
                parametros[key] = True if match.group(1).lower() == 'si' else False
            elif key == 'entrecomidas':
                entre_comidas = match.group(1).lower()
                if entre_comidas in ['nunca', 'aveces', 'siempre']:
                    parametros[key] = entre_comidas
                else:
                    parametros[key] = None
            elif key == 'comidascaloricas':
                parametros[key] = True if match.group(1).lower() == 'si' else False
            else:
                parametros[key] = match.group(1).strip()
    
    return parametros

# Ejemplo de uso con tu frase
frase = "hola me llamo diego Loja mi cedula es 0107345673, tengo una altura de 1,65, mi edad es 25 mi correo es diego@gmail.com mi peso es de 64kilos mi hhistorial familiar es que son gorditos mi familia, entre comidas aveces como y las comidas caloricas si como"
parametros = extraer_parametros(frase)

# Imprimir los resultados obtenidos
print("Parámetros extraídos:")
print(parametros)
