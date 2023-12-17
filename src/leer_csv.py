import csv

def leer_strings_de_fila():
    try:
        with open('whitelist.csv', 'r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file, delimiter='%')
            first_row = next(reader, None)  # Leer la primera fila
            return first_row if first_row is not None else []  # Devolver la primera fila como un array o una lista vacía si no hay datos

    except FileNotFoundError:
        print("No se pudo encontrar el archivo CSV.")
        return []
    except Exception as e:
        print(f"Ocurrió un error: {e}")
        return []
    
def comprobar_whitelist(usuario):
    whitelist = leer_strings_de_fila()

    if usuario in whitelist:
        return 1
    else:
        return 0