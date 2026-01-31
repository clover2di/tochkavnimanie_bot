"""
User input validation utilities.
"""
import re
from typing import Tuple, Optional


def validate_fio(text: str) -> Tuple[bool, str, Optional[str]]:
    """
    Validate and normalize full name (ФИО).
    
    Rules:
    - Minimum 2 words (имя фамилия)
    - Each word starts with capital letter
    - Only letters, spaces, hyphens allowed
    - Min length 5 characters
    
    Args:
        text: Raw input text
        
    Returns:
        Tuple of (is_valid, error_message or normalized_value, normalized_value or None)
    """
    if not text or len(text.strip()) < 5:
        return False, "❌ ФИО слишком короткое. Введите полностью (например: Иванов Иван Иванович).", None
    
    # Remove extra spaces
    text = ' '.join(text.split())
    
    # Check for minimum 2 words
    words = text.split()
    if len(words) < 2:
        return False, "❌ Введите минимум фамилию и имя (например: Иванов Иван).", None
    
    # Check for valid characters (Cyrillic, Latin, hyphens, spaces)
    if not re.match(r'^[а-яёА-ЯЁa-zA-Z\s\-]+$', text):
        return False, "❌ ФИО должно содержать только буквы. Без цифр и спецсимволов.", None
    
    # Normalize: capitalize each word
    normalized = ' '.join(word.capitalize() for word in words)
    
    return True, normalized, normalized


def validate_city(text: str) -> Tuple[bool, str, Optional[str]]:
    """
    Validate and normalize city/town name.
    
    Rules:
    - Min 2 characters
    - Only letters, spaces, hyphens, dots allowed
    
    Returns:
        Tuple of (is_valid, error_message or normalized_value, normalized_value or None)
    """
    if not text or len(text.strip()) < 2:
        return False, "❌ Название населённого пункта слишком короткое.", None
    
    # Remove extra spaces
    text = ' '.join(text.split())
    
    # Check for valid characters
    if not re.match(r'^[а-яёА-ЯЁa-zA-Z\s\-\.0-9]+$', text):
        return False, "❌ Некорректное название. Используйте только буквы.", None
    
    # Normalize: capitalize first letter of each word
    words = text.split()
    normalized = ' '.join(
        word.capitalize() if not word[0].isdigit() else word 
        for word in words
    )
    
    return True, normalized, normalized


def validate_school(text: str) -> Tuple[bool, str, Optional[str]]:
    """
    Validate and normalize school name.
    
    Rules:
    - Min 3 characters
    - Can contain numbers (school №123)
    
    Returns:
        Tuple of (is_valid, error_message or normalized_value, normalized_value or None)
    """
    if not text or len(text.strip()) < 3:
        return False, "❌ Название учебного заведения слишком короткое.", None
    
    # Remove extra spaces
    text = ' '.join(text.split())
    
    # Normalize common abbreviations
    text = text.replace('№', '№ ').replace('  ', ' ')
    
    return True, text, text


def validate_grade(text: str) -> Tuple[bool, str, Optional[str]]:
    """
    Validate and normalize grade (class number).
    
    Rules:
    - Must be a number from 1 to 11
    - Can have letter suffix (10А, 11Б)
    
    Returns:
        Tuple of (is_valid, error_message or normalized_value, normalized_value or None)
    """
    if not text:
        return False, "❌ Укажите класс.", None
    
    text = text.strip().upper()
    
    # Extract number
    match = re.match(r'^(\d{1,2})\s*([А-ЯЁA-Z])?$', text)
    
    if not match:
        return False, "❌ Укажите класс числом от 1 до 11 (например: 9 или 10А).", None
    
    grade_num = int(match.group(1))
    grade_letter = match.group(2) or ""
    
    if grade_num < 1 or grade_num > 11:
        return False, "❌ Класс должен быть от 1 до 11.", None
    
    normalized = f"{grade_num}{grade_letter}"
    
    return True, normalized, normalized


# Validation error messages for display
VALIDATION_ERRORS = {
    "fio": "Введите ФИО полностью (Фамилия Имя Отчество):",
    "city": "Введите название населённого пункта:",
    "school": "Введите полное название учебного заведения:",
    "grade": "Введите номер класса (1-11):"
}
