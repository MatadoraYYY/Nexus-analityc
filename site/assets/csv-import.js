'use strict';
(function () {
  const MAX_BYTES = 10 * 1024 * 1024;
  const MAX_ROWS = 100000;
  const ACTIVE_EVENTS = new Set(['project_created', 'task_created', 'meaningful_action']);
  const REGISTRATION_EVENTS = new Set(['registration', 'register', 'signup', 'регистрация']);
  const aliases = {
    user_id: ['user_id', 'user', 'userid', 'пользователь', 'ид_пользователя'],
    event_name: ['event_name', 'event', 'event_type', 'событие', 'тип_события'],
    event_at: ['event_at', 'timestamp', 'event_time', 'date', 'дата', 'дата_события'],
    revenue: ['revenue', 'amount', 'gross_amount', 'выручка', 'сумма'],
    channel: ['channel', 'канал'],
    feature_name: ['feature_name', 'feature', 'функция'],
  };
  const escapeHtml = value => String(value ?? '').replace(/[&<>'"]/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  const normalize = value => String(value).trim().toLowerCase().replace(/\s+/g, '_');
  const unique = values => new Set(values).size;
  const percent = (part, total) => total ? part / total * 100 : null;
  const format = (value, digits = 0) => value == null ? 'Нет данных' : new Intl.NumberFormat('ru-RU', {maximumFractionDigits: digits}).format(value);
  const formatMoney = value => value == null ? 'Нет данных' : new Intl.NumberFormat('ru-RU', {style:'currency', currency:'RUB', maximumFractionDigits:2}).format(value);

  function detectDelimiter(text) {
    const scores = {',': 0, ';': 0, '\t': 0};
    let quoted = false;
    for (let index = 0; index < Math.min(text.length, 10000); index += 1) {
      const char = text[index];
      if (char === '"') {
        if (quoted && text[index + 1] === '"') index += 1;
        else quoted = !quoted;
      } else if (!quoted && (char === '\n' || char === '\r')) break;
      else if (!quoted && Object.hasOwn(scores, char)) scores[char] += 1;
    }
    return Object.entries(scores).sort((left, right) => right[1] - left[1])[0][0];
  }

  function parseCsv(text) {
    if (!text.trim()) throw new Error('Файл пуст.');
    const delimiter = detectDelimiter(text);
    const matrix = [];
    let row = [], field = '', quoted = false;
    for (let index = 0; index < text.length; index += 1) {
      const char = text[index];
      if (quoted) {
        if (char === '"' && text[index + 1] === '"') { field += '"'; index += 1; }
        else if (char === '"') quoted = false;
        else field += char;
      } else if (char === '"' && field === '') quoted = true;
      else if (char === delimiter) { row.push(field); field = ''; }
      else if (char === '\n' || char === '\r') {
        if (char === '\r' && text[index + 1] === '\n') index += 1;
        row.push(field); field = '';
        if (row.some(cell => cell.trim() !== '')) matrix.push(row);
        row = [];
        if (matrix.length > MAX_ROWS + 1) throw new Error(`Допустимо не более ${MAX_ROWS.toLocaleString('ru-RU')} строк.`);
      } else field += char;
    }
    if (quoted) throw new Error('Не закрыта кавычка в CSV.');
    row.push(field);
    if (row.some(cell => cell.trim() !== '')) matrix.push(row);
    if (matrix.length < 2) throw new Error('В файле нет строк данных.');
    const headers = matrix[0].map((header, index) => (index === 0 ? header.replace(/^\uFEFF/, '') : header).trim());
    if (headers.some(header => !header)) throw new Error('Названия столбцов не могут быть пустыми.');
    if (unique(headers.map(normalize)) !== headers.length) throw new Error('Названия столбцов должны быть уникальными.');
    const rows = matrix.slice(1).map(values => Object.fromEntries(headers.map((header, index) => [header, (values[index] ?? '').trim()])));
    return {headers, rows, delimiter: delimiter === '\t' ? 'табуляция' : delimiter};
  }

  function mapColumns(headers) {
    const normalized = new Map(headers.map(header => [normalize(header), header]));
    return Object.fromEntries(Object.entries(aliases).map(([key, names]) => [key, names.map(name => normalized.get(normalize(name))).find(Boolean) || null]));
  }

  function analyse(parsed) {
    const columns = mapColumns(parsed.headers);
    const missing = ['user_id', 'event_name', 'event_at'].filter(key => !columns[key]);
    if (missing.length) throw new Error(`Не найдены обязательные столбцы: ${missing.join(', ')}.`);
    const valid = [], rejected = [];
    for (const row of parsed.rows) {
      const userId = row[columns.user_id];
      const eventName = row[columns.event_name];
      const timestamp = new Date(row[columns.event_at]);
      if (!userId || !eventName || Number.isNaN(timestamp.getTime())) rejected.push(row);
      else valid.push({row, userId, eventName: normalize(eventName), timestamp});
    }
    if (!valid.length) throw new Error('Не найдено ни одной корректной строки события.');
    const reportDate = new Date(Math.max(...valid.map(item => item.timestamp.getTime())));
    const recognized = valid.some(item => ACTIVE_EVENTS.has(item.eventName));
    const active = valid.filter(item => recognized ? ACTIVE_EVENTS.has(item.eventName) : !REGISTRATION_EVENTS.has(item.eventName));
    const since = days => new Set(active.filter(item => item.timestamp >= new Date(reportDate.getTime() - (days - 1) * 86400000)).map(item => item.userId));
    const dayKey = value => value.toISOString().slice(0, 10);
    const dau = new Set(active.filter(item => dayKey(item.timestamp) === dayKey(reportDate)).map(item => item.userId));
    const wau = since(7), mau = since(30);
    const eventCounts = new Map(), channelCounts = new Map(), featureCounts = new Map();
    for (const item of valid) {
      eventCounts.set(item.eventName, (eventCounts.get(item.eventName) || 0) + 1);
      if (columns.channel && item.row[columns.channel]) channelCounts.set(item.row[columns.channel], (channelCounts.get(item.row[columns.channel]) || 0) + 1);
      if (columns.feature_name && item.row[columns.feature_name]) featureCounts.set(item.row[columns.feature_name], (featureCounts.get(item.row[columns.feature_name]) || 0) + 1);
    }
    let revenue = null;
    if (columns.revenue) revenue = valid.reduce((sum, item) => { const value = Number(String(item.row[columns.revenue]).replace(',', '.')); return sum + (Number.isFinite(value) ? value : 0); }, 0);
    let activated = null;
    if (valid.some(item => item.eventName === 'project_created') && valid.some(item => item.eventName === 'task_created')) {
      const byUser = new Map();
      valid.forEach(item => { if (!byUser.has(item.userId)) byUser.set(item.userId, []); byUser.get(item.userId).push(item); });
      activated = [...byUser.values()].filter(events => {
        const projects = events.filter(item => item.eventName === 'project_created').map(item => item.timestamp);
        const tasks = events.filter(item => item.eventName === 'task_created').map(item => item.timestamp);
        return projects.some(project => tasks.some(task => task >= project && task - project <= 7 * 86400000));
      }).length;
    }
    const duplicates = parsed.rows.length - new Set(parsed.rows.map(row => parsed.headers.map(header => row[header]).join('\u001f'))).size;
    const top = source => [...source.entries()].sort((left, right) => right[1] - left[1]).slice(0, 10);
    return {valid, rejected, reportDate, users: unique(valid.map(item => item.userId)), dau: dau.size, wau: wau.size, mau: mau.size, stickiness: percent(dau.size, mau.size), revenue, activated, duplicates, events: top(eventCounts), channels: top(channelCounts), features: top(featureCounts)};
  }

  const metricCard = (label, value, context) => `<article class="card"><div class="label">${escapeHtml(label)}</div><div class="value">${escapeHtml(value)}</div><div class="context">${escapeHtml(context)}</div></article>`;
  const rowsTable = (headers, rows) => `<div class="table-wrap"><table><thead><tr>${headers.map(value => `<th>${escapeHtml(value)}</th>`).join('')}</tr></thead><tbody>${rows.map(row => `<tr>${row.map(value => `<td>${escapeHtml(value)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  const day = value => new Intl.DateTimeFormat('ru-RU', {dateStyle:'medium'}).format(value);

  function resultHtml(file, parsed, result) {
    const preview = parsed.rows.slice(0, 20).map(row => parsed.headers.map(header => row[header]));
    const quality = [['Размер файла', file.size <= MAX_BYTES, `${format(file.size / 1024, 1)} КБ`], ['Структура CSV', true, `${parsed.headers.length} столбцов, разделитель: ${parsed.delimiter}`], ['Корректные события', result.valid.length > 0, `${result.valid.length} из ${parsed.rows.length}`], ['Некорректные строки', result.rejected.length === 0, `${result.rejected.length}`], ['Полные дубликаты', result.duplicates === 0, `${result.duplicates}`]];
    return `<div class="local-banner"><strong>Локальный набор активен:</strong> ${escapeHtml(file.name)}. Данные существуют только в памяти этой вкладки.</div><div class="grid import-metrics">${metricCard('Пользователи', format(result.users), 'Уникальные идентификаторы')}${metricCard('События', format(result.valid.length), `Отброшено: ${result.rejected.length}`)}${metricCard('Активные за день', format(result.dau), day(result.reportDate))}${metricCard('Активные за неделю', format(result.wau), 'Последние 7 дней')}${metricCard('Активные за месяц', format(result.mau), 'Последние 30 дней')}${metricCard('Вовлечённость', result.stickiness == null ? 'Нет данных' : `${format(result.stickiness, 1)}%`, 'День / месяц')}${metricCard('Активированные', format(result.activated), result.activated == null ? 'Нужны project_created и task_created' : 'Последовательность за 7 дней')}${metricCard('Выручка', formatMoney(result.revenue), result.revenue == null ? 'Не найден столбец суммы' : 'Сумма корректных значений')}</div><div class="two"><section class="panel"><h2>Популярные события</h2>${rowsTable(['Событие','Количество'], result.events.map(([name,count]) => [name,count]))}</section><section class="panel"><h2>Качество импорта</h2>${rowsTable(['Проверка','Результат','Подробности'], quality.map(([name, passed, detail]) => [name, passed ? 'Пройдена' : 'Предупреждение', detail]))}</section></div>${result.channels.length ? `<section class="panel"><h2>Каналы</h2>${rowsTable(['Канал','События'],result.channels)}</section>` : ''}${result.features.length ? `<section class="panel"><h2>Функции</h2>${rowsTable(['Функция','События'],result.features)}</section>` : ''}<section class="panel"><h2>Предпросмотр первых 20 строк</h2>${rowsTable(parsed.headers, preview)}</section>`;
  }

  function pageHtml() {
    return `<section class="panel import-panel"><h2>Локальный импорт CSV</h2><p>Файл обрабатывается только в вашем браузере: содержимое не отправляется в NEXUS, GitHub или Cloudflare и не сохраняется после закрытия вкладки.</p><div id="csv-drop" class="drop-zone" tabindex="0" role="button" aria-label="Выбрать CSV-файл"><strong>Перетащите CSV сюда</strong><span>или выберите файл размером до 10 МБ и 100 000 строк</span><button id="csv-select" class="primary-button" type="button">Выбрать CSV</button><input id="csv-file" type="file" accept=".csv,text/csv" hidden></div><div class="import-actions"><button id="csv-sample" class="secondary-button" type="button">Скачать пример CSV</button><button id="csv-reset" class="secondary-button" type="button">Сбросить локальные данные</button></div><details><summary>Требования к файлу</summary><p>Обязательные столбцы: <code>user_id</code>, <code>event_name</code>, <code>event_at</code>. Дополнительные: <code>revenue</code>, <code>channel</code>, <code>feature_name</code>. Поддерживаются запятая, точка с запятой и табуляция, UTF-8 и поля в кавычках.</p></details><div id="csv-message" class="import-message" aria-live="polite"></div></section><div id="csv-results"></div>`;
  }

  async function processFile(file) {
    const message = document.querySelector('#csv-message'), results = document.querySelector('#csv-results');
    if (!file) return;
    results.innerHTML = '';
    if (file.size > MAX_BYTES) { message.className = 'import-message error-box'; message.textContent = 'Файл превышает допустимый размер 10 МБ.'; return; }
    message.className = 'import-message'; message.textContent = 'Чтение и проверка файла…';
    try {
      const parsed = parseCsv(await file.text()), result = analyse(parsed);
      message.className = 'import-message success-box'; message.textContent = `Импорт завершён: обработано ${parsed.rows.length.toLocaleString('ru-RU')} строк.`;
      results.innerHTML = resultHtml(file, parsed, result);
    } catch (error) { message.className = 'import-message error-box'; message.textContent = error instanceof Error ? error.message : 'Не удалось обработать CSV.'; }
  }

  function downloadSample() {
    const content = '\uFEFFuser_id,event_name,event_at,revenue,channel,feature_name\nusr_001,registration,2026-09-01T09:00:00,0,Органический поиск,\nusr_001,project_created,2026-09-01T09:05:00,0,Органический поиск,Совместная работа\nusr_001,task_created,2026-09-01T09:15:00,990,Органический поиск,Автоматизация\nusr_002,meaningful_action,2026-09-02T12:00:00,0,Партнёрства,Отчёты\n';
    const link = document.createElement('a'); link.href = URL.createObjectURL(new Blob([content], {type:'text/csv;charset=utf-8'})); link.download = 'nexus-example.csv'; link.click(); URL.revokeObjectURL(link.href);
  }

  function render() {
    document.querySelectorAll('.nav').forEach(button => button.classList.toggle('active', button.dataset.view === 'import'));
    document.querySelector('#crumb').textContent = 'Импорт CSV'; document.querySelector('#title').textContent = 'Локальный импорт CSV'; document.querySelector('#subtitle').textContent = 'Анализ собственных событий без backend и загрузки данных на сервер'; document.querySelector('#view').innerHTML = pageHtml(); history.replaceState(null, '', '#import');
    const input = document.querySelector('#csv-file'), drop = document.querySelector('#csv-drop');
    document.querySelector('#csv-select').addEventListener('click', event => { event.stopPropagation(); input.click(); }); input.addEventListener('change', () => processFile(input.files[0])); drop.addEventListener('click', () => input.click()); drop.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); input.click(); } });
    for (const type of ['dragenter','dragover']) drop.addEventListener(type, event => { event.preventDefault(); drop.classList.add('dragging'); }); for (const type of ['dragleave','drop']) drop.addEventListener(type, event => { event.preventDefault(); drop.classList.remove('dragging'); }); drop.addEventListener('drop', event => processFile(event.dataTransfer.files[0]));
    document.querySelector('#csv-sample').addEventListener('click', downloadSample); document.querySelector('#csv-reset').addEventListener('click', render); document.querySelector('#navigation').classList.remove('open');
  }

  function install() {
    const quality = document.querySelector('[data-view="quality"]'); if (!quality || document.querySelector('[data-view="import"]')) return;
    const button = document.createElement('button'); button.className = 'nav'; button.dataset.view = 'import'; button.textContent = 'Импорт CSV'; quality.before(button);
    document.addEventListener('click', event => { const target = event.target.closest('[data-view="import"]'); if (!target) return; event.preventDefault(); event.stopImmediatePropagation(); render(); }, true);
    if (location.hash === '#import') setTimeout(render, 0);
  }

  window.NexusCsvImport = {parseCsv, mapColumns, analyse, processFile, render};
  if (typeof document !== 'undefined') document.addEventListener('DOMContentLoaded', install);
}());
