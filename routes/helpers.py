import json
import os
import re

def get_data(file_path):
    if not os.path.exists(file_path):
        return {
            'storages': [], 
            'samples': [],
            'measurements': [],
            'experiments': []
        }
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Гарантируем наличие ключей
            if 'storages' not in data: data['storages'] = []
            if 'samples' not in data: data['samples'] = []
            if 'measurements' not in data: data['measurements'] = []
            if 'experiments' not in data: data['experiments'] = []
            return data
    except Exception:
        return {
            'storages': [], 
            'samples': [],
            'measurements': [],
            'experiments': []
        }

def save_data(file_path, data):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def transliterate(text):
    if not text:
        return "unnamed"
    
    mapping = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'h', 'ц': 'c', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch', 'ъ': '',
        'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
        'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
        'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
        'Ф': 'F', 'Х': 'H', 'Ц': 'C', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sch', 'Ъ': '',
        'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
    }
    
    result = ""
    for char in text:
        if char in mapping:
            result += mapping[char]
        elif char.isalnum() or char in " -_.":
            result += char
        else:
            result += "_"
    
    result = re.sub(r'\s+', '_', result.strip())
    result = re.sub(r'[^A-Za-z0-9_.-]', '_', result)
    
    return result if result else "unnamed"