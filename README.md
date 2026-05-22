# 🎨 Minigramm — Мини Instagram на Django

## Быстрый старт

```bash
# 1. Установить зависимости
pip install django pillow

# 2. Применить миграции
python manage.py migrate

# 3. Создать суперпользователя (опционально)
python manage.py createsuperuser

# 4. Запустить сервер
python manage.py runserver
```

Открыть: **http://127.0.0.1:8000**

## Тестовые аккаунты
| Логин | Пароль |
|-------|--------|
| anna_k | demo1234 |
| max_tech | demo1234 |
| demo | demo1234 |

## Функциональность
- ✅ Регистрация и вход
- ✅ Лента постов (от подписанных)
- ✅ Создание постов с фото и/или текстом
- ✅ Лайки (без перезагрузки страницы)
- ✅ Комментарии (Ajax)
- ✅ Профиль с сеткой постов
- ✅ Подписки / отписки
- ✅ Поиск пользователей и постов
- ✅ Редактирование профиля с аватаркой

## Стек
- **Backend**: Django 4.x + SQLite
- **Frontend**: Pure CSS + Vanilla JS (без фреймворков)
- **Шрифты**: DM Sans + Playfair Display
- **Дизайн**: Dark theme, Instagram-inspired
