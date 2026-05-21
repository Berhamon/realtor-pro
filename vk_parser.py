import vk_api
import requests
import re
from datetime import datetime
from typing import Optional


class VKParser:
    def __init__(self, token: str):
        self.token = token
        self.vk = None
        self._connect()

    def _connect(self):
        try:
            session = vk_api.VkApi(token=self.token)
            self.vk = session.get_api()
            return True
        except Exception as e:
            print(f"Ошибка подключения к VK: {e}")
            return False

    def _extract_group_id(self, url: str) -> Optional[str]:
        url = url.strip().rstrip("/")
        patterns = [
            r"vk\.com/club(\d+)",
            r"vk\.com/public(\d+)",
            r"vk\.com/([^/]+)$",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def _clean_text(self, text: str) -> str:
        """Очистка текста от лишних символов"""
        # Убираем множественные пустые строки
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Убираем лишние пробелы
        text = re.sub(r'[ \t]+', ' ', text)
        return text.strip()

    def _extract_phones(self, text: str) -> list:
        """
        Извлечение ВСЕХ номеров телефона из текста.
        Поддерживает форматы:
        - 89829177321
        - 8-982-917-73-21
        - +7(982)917-73-21
        - 79199273447
        - 8 982 917 73 21
        - ☎️89044636247 или 89655193084
        """
        # Убираем эмодзи и спецсимволы перед парсингом
        clean = re.sub(r'[☎️📞📱✆🤙]+', ' ', text)

        patterns = [
            # +7 или 8 в начале с разными разделителями
            r'(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}',
            # Просто 11 цифр начинающихся на 7 или 8
            r'(?<!\d)[78]\d{10}(?!\d)',
            # Формат без кода страны: 9XX-XXX-XX-XX
            r'(?<!\d)9\d{2}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}(?!\d)',
        ]

        found = []
        seen_normalized = set()

        for pattern in patterns:
            matches = re.findall(pattern, clean)
            for match in matches:
                # Нормализуем: оставляем только цифры
                digits = re.sub(r'\D', '', match)

                # Приводим к единому формату
                if len(digits) == 10 and digits.startswith('9'):
                    digits = '7' + digits
                elif len(digits) == 11 and digits.startswith('8'):
                    digits = '7' + digits[1:]

                # Проверяем что это валидный РФ номер
                if len(digits) != 11 or not digits.startswith('7'):
                    continue

                if digits not in seen_normalized:
                    seen_normalized.add(digits)
                    # Форматируем красиво
                    formatted = (
                        f"+7 ({digits[1:4]}) "
                        f"{digits[4:7]}-"
                        f"{digits[7:9]}-"
                        f"{digits[9:11]}"
                    )
                    found.append(formatted)

        return found

    def _extract_phone(self, text: str) -> str:
        """Первый телефон или 'Не указан'"""
        phones = self._extract_phones(text)
        return phones[0] if phones else "Не указан"

    def _extract_all_phones_str(self, text: str) -> str:
        """Все телефоны через запятую"""
        phones = self._extract_phones(text)
        if not phones:
            return "Не указан"
        return " / ".join(phones)

    def _extract_address(self, text: str) -> str:
        """
        Умное извлечение адреса из текста.
        Ищет улицы, районы, ориентиры.
        """
        # Паттерны для улиц
        street_patterns = [
            # ул. Название, дом
            r'(?:ул\.|улица|пр\.|проспект|пер\.|переулок|'
            r'бул\.|бульвар|пл\.|площадь|ш\.|шоссе|'
            r'наб\.|набережная|туп\.|тупик)\s+'
            r'[\w\s\.]+(?:,\s*\d+[\w\/]*)?',

            # Название + ул.
            r'[\w]+\s+(?:ул\.|улица|пр\.|проспект)',

            # Адрес после слова "адрес:"
            r'(?:адрес|находится по адресу)\s*:?\s*([^\n,]+)',

            # Чкалова 20, Ленина 5 и т.п. (улица без приставки)
            r'\b(?:на\s+)?([А-ЯЁ][а-яё]+(?:а|ого|ева|ова)?)\s+(\d+(?:[а-яё])?)'
            r'(?:\s*\((?:[^)]+)\))?',
        ]

        for pattern in street_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result = match.group(0).strip()
                # Убираем мусор в конце
                result = re.sub(r'[,\.\s]+$', '', result)
                if len(result) > 5:
                    return result

        # Ищем район
        district = self._extract_district(text)
        if district:
            return district

        return "Не указан"

    def _extract_district(self, text: str) -> str:
        """Извлечение района/ориентира"""
        district_patterns = [
            # Явное указание района
            r'район[е]?\s*:?\s*([\w\s]+?)(?:\.|,|\n|$)',
            r'р-н\s+([\w\s]+?)(?:\.|,|\n|$)',

            # Остановка как ориентир
            r'остановк[аи]\s+["\']?([\w\s]+?)["\']?'
            r'(?:\.|,|\n|$)',

            # Около/рядом с чем-то
            r'(?:около|рядом|напротив|у|возле)\s+'
            r'([\w\s]+?)(?:\.|,|\n|$)',

            # "на Чкалова", "на Ленина" и т.д.
            r'на\s+([А-ЯЁ][а-яё]+(?:а|ого)?)\s*(?:\d+)?',
        ]

        for pattern in district_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result = match.group(1).strip()
                result = re.sub(r'[,\.\s]+$', '', result)
                if 3 < len(result) < 60:
                    return f"Район: {result}"

        return ""

    def _extract_price(self, text: str) -> str:
        """
        Умное извлечение цены аренды.
        Различает цену аренды и залог/комиссию.
        """
        # Сначала ищем явные упоминания аренды
        rent_patterns = [
            # "15 тыс", "15000 руб", "15 000 ₽"
            r'(?:аренда|стоимость|цена|оплата|'
            r'сдается за|сдаётся за)\s*:?\s*'
            r'(\d[\d\s]*)\s*(?:тыс(?:яч)?\.?|руб(?:лей|\.)?|₽|р\.)',

            # Просто число + валюта в начале предложения
            r'(?:^|\n)\s*(\d[\d\s]{2,})\s*(?:тыс(?:яч)?\.?|руб(?:лей|\.)?|₽)',

            # "X рублей/месяц" или "X р/мес"
            r'(\d[\d\s]*)\s*(?:руб(?:лей|\.)?|₽|р\.)\s*'
            r'(?:/|в)\s*(?:мес(?:яц)?\.?|месяц)',

            # "X тысяч в месяц"
            r'(\d+(?:[.,]\d+)?)\s*тыс(?:яч)?\.?\s*'
            r'(?:\+|в месяц|/мес)?',

            # Общий паттерн с валютой
            r'(\d[\d\s]{1,})\s*(?:тыс(?:яч)?\.?|руб(?:лей|\.)?|₽|р\.)',
        ]

        # Слова которые указывают что это НЕ цена аренды
        exclude_keywords = [
            'залог', 'задаток', 'депозит', 'комиссия',
            'продается', 'продаётся', 'стоимость квартиры',
            'цена квартиры', 'торг', 'площадь'
        ]

        text_lower = text.lower()

        for pattern in rent_patterns:
            for match in re.finditer(pattern, text_lower):
                # Проверяем контекст — нет ли рядом стоп-слов
                start = max(0, match.start() - 30)
                context = text_lower[start:match.start()]

                if any(kw in context for kw in exclude_keywords):
                    continue

                price_str = match.group(1).replace(' ', '').replace(',', '.')

                try:
                    price_val = float(price_str)

                    # "тыс" → умножаем
                    if 'тыс' in match.group(0).lower():
                        price_val *= 1000

                    # Разумные рамки цены аренды (1000 - 500000)
                    if 1000 <= price_val <= 500000:
                        # Форматируем красиво
                        price_int = int(price_val)
                        formatted = f"{price_int:,}".replace(",", " ")
                        return f"{formatted} ₽/мес"
                except ValueError:
                    continue

        return "Не указана"

    def _extract_rooms(self, text: str) -> str:
        """Улучшенное определение количества комнат"""
        text_lower = text.lower()

        # Студия
        if re.search(r'студи[яю]', text_lower):
            return "Студия"

        # Комната (не квартира)
        if re.search(r'\bкомнат[уаы]\b(?!\s*квартир)', text_lower):
            if not re.search(r'\d+[\s-]*комнат', text_lower):
                return "Комната"

        # Числовые варианты: "1-комн", "однокомнатная" и т.д.
        patterns = [
            (r'(?:1|одно|одн)[о-]?[\s-]*комнат', "1-комнатная"),
            (r'(?:2|двух|двух)[х-]?[\s-]*комнат', "2-комнатная"),
            (r'(?:3|трёх|трех|трёх)[х-]?[\s-]*комнат', "3-комнатная"),
            (r'(?:4|четырёх|четырех)[х-]?[\s-]*комнат', "4-комнатная"),
            (r'(?:5|пяти)[х-]?[\s-]*комнат', "5-комнатная"),

            # Сокращения: "1к", "2к квартира"
            (r'\b1\s*[кk][\s-]*(?:квартир|кв\.?)?', "1-комнатная"),
            (r'\b2\s*[кk][\s-]*(?:квартир|кв\.?)?', "2-комнатная"),
            (r'\b3\s*[кk][\s-]*(?:квартир|кв\.?)?', "3-комнатная"),

            # "однушка", "двушка"
            (r'\bоднушк', "1-комнатная"),
            (r'\bдвушк', "2-комнатная"),
            (r'\bтрёшк|\bтрешк', "3-комнатная"),
        ]

        for pattern, result in patterns:
            if re.search(pattern, text_lower):
                return result

        return "Не указано"

    def _extract_area(self, text: str) -> str:
        """Извлечение площади"""
        patterns = [
            r'(\d+(?:[.,]\d+)?)\s*кв\.?\s*м',
            r'площадь\s*:?\s*(\d+(?:[.,]\d+)?)',
            r'(\d+(?:[.,]\d+)?)\s*м²',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return f"{match.group(1)} м²"
        return ""

    def _extract_floor(self, text: str) -> str:
        """Извлечение этажа"""
        patterns = [
            r'(\d+)\s*этаж(?!\s*из)',
            r'этаж\s*:?\s*(\d+)',
            r'\((\d+)\s*эт',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return f"{match.group(1)} этаж"
        return ""

    def _extract_contact_name(self, text: str) -> str:
        """Извлечение имени контакта"""
        patterns = [
            # "☎️89829177321 Олеся" — имя после телефона
            r'(?:\+7|8)[\d\s\-\(\)]{9,}\s+([А-ЯЁ][а-яё]+)',

            # "Обращаться к Ивану"
            r'обращаться\s+к\s+([А-ЯЁ][а-яё]+)',

            # "Собственник Анна"
            r'(?:собственник|хозяин|хозяйка)\s+([А-ЯЁ][а-яё]+)',

            # АН "Название" или агентство
            r'АН\s+["\']([^"\']+)["\']',
            r'агентство\s+["\']?([^"\'\.]+)["\']?',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if len(name) > 1:
                    return name
        return ""

    def _is_rent_post(self, text: str) -> bool:
        """Проверка что пост про аренду"""
        text_lower = text.lower()

        rent_keywords = [
            'сдается', 'сдаётся', 'сдам', 'сдаю',
            'аренда', 'снять', 'в аренду',
            'на длительный', 'на длительный срок',
            'комнату', 'квартиру', 'студию'
        ]

        # Исключаем посты о продаже (если нет слов аренды)
        sell_keywords = ['продается', 'продаётся', 'продам', 'куплю']

        has_rent = any(kw in text_lower for kw in rent_keywords)
        has_sell = any(kw in text_lower for kw in sell_keywords)

        # Если есть и аренда и продажа — считаем арендой
        return has_rent or (not has_sell and len(text) > 50)

    def get_posts(self, group_url: str, count: int = 50) -> list:
        """Получение и парсинг постов из группы"""
        if not self.vk:
            return []

        group_id = self._extract_group_id(group_url)
        if not group_id:
            return []

        posts_data = []

        try:
            # Название группы
            try:
                info = self.vk.groups.getById(group_id=group_id)
                group_name = info[0].get("name", group_id)
            except Exception:
                group_name = group_id

            # Посты
            response = self.vk.wall.get(
                domain=group_id,
                count=count,
                filter="all"
            )

            for item in response.get("items", []):
                text = item.get("text", "")

                if not text or len(text) < 15:
                    continue

                if not self._is_rent_post(text):
                    continue

                # Чистим текст
                text = self._clean_text(text)

                # Фотографии
                photos = []
                for attach in item.get("attachments", []):
                    if attach.get("type") == "photo":
                        sizes = attach["photo"].get("sizes", [])
                        if sizes:
                            best = max(sizes, key=lambda x: x.get("width", 0))
                            url = best.get("url", "")
                            if url:
                                photos.append(url)

                # Все телефоны
                phones_list = self._extract_phones(text)
                phones_str = self._extract_all_phones_str(text)

                # Дата
                ts = item.get("date", 0)
                pub_date = datetime.fromtimestamp(ts).strftime("%d.%m.%Y %H:%M")

                # Ссылка
                owner_id = item.get("owner_id", "")
                post_id = item.get("id", "")
                post_url = f"https://vk.com/wall{owner_id}_{post_id}"

                # Доп. поля
                area = self._extract_area(text)
                floor = self._extract_floor(text)
                contact = self._extract_contact_name(text)

                post = {
                    "id": f"{owner_id}_{post_id}",
                    "text": text,
                    "photos": photos,

                    # Контакты
                    "phone": phones_str,          # Строка со всеми номерами
                    "phones_list": phones_list,   # Список отдельных номеров
                    "contact_name": contact,

                    # Характеристики
                    "address": self._extract_address(text),
                    "price": self._extract_price(text),
                    "rooms": self._extract_rooms(text),
                    "area": area,
                    "floor": floor,

                    # Мета
                    "date": pub_date,
                    "url": post_url,
                    "group": group_name,
                    "group_url": group_url,

                    # Статус
                    "status": "search",
                    "notes": "",
                }

                posts_data.append(post)

        except vk_api.exceptions.ApiError as e:
            print(f"VK API ошибка: {e}")
        except Exception as e:
            print(f"Ошибка: {e}")

        return posts_data

    def get_posts_from_all_groups(
        self,
        group_urls: list,
        count_per_group: int = 50,
        callback=None
    ) -> list:
        all_posts = []
        for i, url in enumerate(group_urls):
            if callback:
                callback(f"Группа {i+1}/{len(group_urls)}: {url}")
            posts = self.get_posts(url, count_per_group)
            all_posts.extend(posts)
        return all_posts