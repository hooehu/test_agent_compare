# figma-visual-checker

Автоматическое сравнение Figma-макетов с реальными страницами через Claude Vision.

## Установка

```bash
pip install -r requirements.txt
playwright install chromium
```

## Настройка

1. Скопируй `config.yaml` и заполни `figma_file_key` и `figma_node_id` для каждой страницы.
2. Установи переменные окружения:

```bash
export FIGMA_TOKEN=fig_xxxxx          # Figma → Account Settings → Access tokens
export ANTHROPIC_API_KEY=sk-ant-xxx
```

## Запуск

```bash
python runner.py --config config.yaml
```

Открой `output/report.html` в браузере.

## Как найти figma_node_id

1. Открой файл в Figma
2. Кликни правой кнопкой на нужный фрейм → "Copy link"
3. В ссылке вида `?node-id=123-456` — это и есть node_id (замени `-` на `:` → `123:456`)
