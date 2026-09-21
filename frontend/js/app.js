import { api, demo, managedPreview, previewLabel } from './api.js?v=session-v3';

const icons = {
  grid: '<rect x="3" y="3" width="7" height="7" rx="1.7"/><rect x="14" y="3" width="7" height="7" rx="1.7"/><rect x="3" y="14" width="7" height="7" rx="1.7"/><rect x="14" y="14" width="7" height="7" rx="1.7"/>',
  calendar: '<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M16 3v4M8 3v4M3 11h18m-13 4h2m4 0h2m-8 3h2"/>',
  users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2m20 0v-2a4 4 0 0 0-3-3.9M15 3.1a4 4 0 0 1 0 7.8"/><circle cx="9" cy="7" r="4"/>',
  flower: '<path d="M12 9c-7-10-13 0-4 4-10 6 0 14 4 3 5 10 14 2 4-3 10-5 2-14-4-4Z"/><circle cx="12" cy="12" r="2"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  history: '<path d="M3 11a9 9 0 1 1 2.5 7M3 4v7h7m2-4v5l3 2"/>',
  settings: '<path d="m9 3-1 3-3 1-2 4 2 2v4l4 3 3-1 3 1 4-3v-4l2-2-2-4-3-1-1-3Z"/><circle cx="12" cy="12" r="3"/>',
  search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4.5 4.5"/>',
  bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  chevron: '<path d="m9 5 7 7-7 7"/>',
  down: '<path d="m6 9 6 6 6-6"/>',
  arrow: '<path d="M5 12h14m-6-6 6 6-6 6"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  checkCircle: '<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
  money: '<rect x="3" y="5" width="18" height="15" rx="3"/><path d="M3 9h18m-6 5h6"/><circle cx="16" cy="14" r=".5"/>',
  trend: '<path d="m3 17 6-6 4 4 8-11m-6 0h6v6"/>',
  more: '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
  lock: '<rect x="4" y="10" width="16" height="11" rx="3"/><path d="M8 10V7a4 4 0 0 1 8 0v3m-4 5v2"/>',
  help: '<circle cx="12" cy="12" r="9"/><path d="M9 9a3 3 0 0 1 6 0c0 2-3 2-3 4m0 3h.01"/>',
  logout: '<path d="M9 4H4v16h5m5-13 5 5-5 5m-6-5h11"/>',
  close: '<path d="m6 6 12 12M6 18 18 6"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  edit: '<path d="m15 4 5 5M4 20l5-1L21 7a2 2 0 0 0-4-4L5 15Z"/>',
  mail: '<rect x="3" y="5" width="18" height="14" rx="3"/><path d="m3 6 9 7 9-7"/>',
  spark: '<path d="m12 2 2.6 7.4L22 12l-7.4 2.6L12 22l-2.6-7.4L2 12l7.4-2.6Z"/>',
  heart: '<path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z"/>',
};
const icon = (name, cls = '') => `<svg class="icon ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name] || icons.flower}</svg>`;
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const money = value => Number(value).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
const today = () => new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Sao_Paulo', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date());
const dateObj = value => new Date(value + 'T12:00:00');
const dateKey = d => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
const prettyDate = (date, options = {}) => dateObj(date).toLocaleDateString('pt-BR', { day: 'numeric', month: 'long', ...options });
const initials = name => (name || '').split(' ').filter(Boolean).slice(0, 2).map(p => p[0]).join('');
const statuses = { pending: 'Pendente', confirmed: 'Confirmado', completed: 'Concluído', cancelled: 'Cancelado', rejected: 'Recusado' };
const statusBadge = status => `<span class="status ${status}"><i></i>${statuses[status]}</span>`;
const avatar = (name, id = 0, size = '') => `<span class="avatar color-${Number(id) % 6} ${size}">${esc(initials(name))}</span>`;
const state = { user: null, services: [], clients: [], appointments: [], hours: [], blocks: [], notifications: [], settings: {}, selectedDate: today(), calendarMonth: dateObj(today()), period: 'day', search: '', statusFilter: '', serviceCategory: '', clientSearch: '', loading: true };
let toastTimer, modalFocus, modalVersion = 0;
const route = () => location.hash.slice(1).split('?')[0] || (state.user ? (state.user.is_staff ? 'painel' : 'inicio') : 'inicio');
const staff = () => state.user?.is_staff;

function toast(message, error = false) {
  const node = document.getElementById('toast');
  node.innerHTML = `${icon(error ? 'help' : 'checkCircle')}<span>${esc(message)}</span>`;
  node.className = `visible ${error ? 'error' : ''}`;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => node.className = '', 4500);
}
function modal(title, subtitle, content, wide = false) {
  modalFocus = document.activeElement;
  modalVersion++;
  document.getElementById('modal-root').innerHTML = `<div class="modal-overlay" data-action="backdrop"><section class="modal ${wide ? 'wide' : ''}" role="dialog" aria-modal="true" aria-labelledby="modal-title"><header><div><h2 id="modal-title">${esc(title)}</h2><p>${esc(subtitle)}</p></div><button class="icon-button" data-action="close-modal" aria-label="Fechar">${icon('close')}</button></header>${content}</section></div>`;
  document.body.classList.add('modal-open');
  setTimeout(() => document.querySelector('.modal input, .modal select, .modal button')?.focus(), 0);
}
function closeModal() { document.getElementById('modal-root').innerHTML = ''; document.body.classList.remove('modal-open'); modalVersion++; modalFocus?.focus(); }
const empty = (title, text, symbol = 'calendar') => `<div class="empty">${icon(symbol)}<h3>${title}</h3><p>${text}</p></div>`;
const field = (label, name, value = '', type = 'text', attrs = '') => `<label class="field"><span>${label}</span><input type="${type}" name="${name}" value="${esc(value)}" ${attrs}></label>`;
const formError = '<div class="form-error" role="alert" hidden></div>';
const cookieHelp = error => error.code === 'csrf_failed' && error.csrfReason === 'cookie_missing'
  ? (managedPreview
    ? '<div class="cookie-help-text">Use o painel de prévia do Arena para acessar esta instância. Não copie a URL e2b.app: ela exige autorização da plataforma. Não há token para preencher no Aura.</div><button type="button" class="button secondary cookie-help" data-action="reload-preview">Recarregar esta prévia</button>'
    : `<a class="button secondary cookie-help" href="${esc(location.href)}" target="_blank" rel="noopener noreferrer">Abrir Aura em nova aba ${icon('arrow')}</a>`) : '';
const submitButton = (label = 'Salvar alterações') => `<div class="form-footer"><button class="button secondary" type="button" data-action="close-modal">Cancelar</button><button class="button primary" type="submit">${label}${icon('arrow')}</button></div>`;

async function loadData() {
  const tasks = [api('/services/'), api('/business-hours/'), api('/settings/')];
  if (state.user) tasks.push(api('/appointments/'), api('/notifications/'));
  if (staff()) tasks.push(api('/clients/'), api('/blocked-slots/'));
  const [services, hours, settings, appointments = [], notifications = [], clients = [], blocks = []] = await Promise.all(tasks);
  Object.assign(state, { services, hours, settings, appointments, notifications, clients, blocks });
}
async function refresh() { await loadData(); render(); }

function sidebar() {
  const page = route();
  const links = staff() ? [['painel', 'grid', 'Visão geral'], ['agenda', 'calendar', 'Minha agenda'], ['clientes', 'users', 'Clientes'], ['servicos', 'flower', 'Serviços']] : [['inicio', 'grid', 'Início'], ['servicos', 'flower', 'Nossos serviços'], ...(state.user ? [['meus-agendamentos', 'calendar', 'Meus agendamentos']] : [])];
  const manage = staff() ? [['horarios', 'clock', 'Horários de atendimento'], ['historico', 'history', 'Histórico'], ['configuracoes', 'settings', 'Configurações']] : state.user ? [['historico', 'history', 'Meu histórico'], ['perfil', 'users', 'Meu perfil']] : [['login', 'users', 'Entrar na minha conta']];
  const navLink = ([key, symbol, label]) => `<a href="#${key}" class="nav-item ${page === key ? 'active' : ''}">${icon(symbol)}<span>${label}</span>${key === 'agenda' && state.appointments.filter(a => a.appointment_date === today() && ['pending', 'confirmed'].includes(a.status)).length ? `<small>${state.appointments.filter(a => a.appointment_date === today() && ['pending', 'confirmed'].includes(a.status)).length}</small>` : ''}</a>`;
  return `<aside class="sidebar"><a href="#${staff() ? 'painel' : 'inicio'}" class="brand"><span class="brand-word">aura<span>✳</span></span><span class="brand-tag">GESTÃO LEVE. BELEZA LIVRE.</span></a>
    <div class="studio-card"><div class="studio-mark">${icon('flower')}</div><div><strong>${esc(state.settings.studio_name || 'Studio Aura')}</strong><span>${staff() ? 'Seu espaço de beleza' : 'Seu momento de cuidado'}</span></div><span class="studio-dot"></span></div>
    <div class="nav-label">PRINCIPAL</div><nav>${links.map(navLink).join('')}</nav><div class="nav-label management">${staff() ? 'GESTÃO' : 'SEU ESPAÇO'}</div><nav>${manage.map(navLink).join('')}</nav>
    <div class="sidebar-bottom"><div class="care-card"><span class="care-icon">${icon('spark')}</span><strong>Você cuida da beleza.<br>A gente cuida do resto.</strong><p>Uma rotina mais organizada<br>começa por aqui.</p><button data-action="help">Conheça o seu Aura ${icon('arrow')}</button></div><button class="support" data-action="help">${icon('help')}Central de ajuda${icon('chevron')}</button><div class="sidebar-footer">Feito para o seu florescer <span>✧</span></div></div>
  </aside>`;
}
function shell(content) {
  const labels = { painel: 'Visão geral', agenda: 'Minha agenda', clientes: 'Clientes', servicos: 'Serviços', horarios: 'Horários de atendimento', historico: 'Histórico', configuracoes: 'Configurações', inicio: 'Bem-vinda ao Aura', perfil: 'Meu perfil', 'meus-agendamentos': 'Meus agendamentos', login: 'Minha conta', cadastro: 'Criar conta', 'recuperar-senha': 'Recuperar senha', 'redefinir-senha': 'Nova senha' };
  return `${sidebar()}<div class="workspace"><header class="topbar"><div class="breadcrumb"><button class="icon-button mobile-menu" data-action="menu" aria-label="Abrir menu">${icon('menu')}</button><span>Meu espaço</span>${icon('chevron')}<strong>${labels[route()] || 'Aura'}</strong></div><div class="top-actions"><button class="top-search" data-action="search">${icon('search')}<span>Buscar no Aura…</span><kbd>⌘ K</kbd></button>${state.user ? `<button class="icon-button notification-button" data-action="notifications" aria-label="Notificações">${icon('bell')}${state.notifications.some(n => !n.read) ? '<i></i>' : ''}</button><span class="header-divider"></span><button class="account-button" data-action="account">${avatar(state.user.name, 1)}<span><strong>${esc(staff() ? state.settings.professional_name : state.user.name.split(' ')[0])}</strong><small>${staff() ? 'Profissional de beleza' : 'Seu momento é agora'}</small></span>${icon('down')}</button>` : `<a href="#login" class="button primary small">Entrar ${icon('arrow')}</a>`}</div></header>
    <main id="main">${previewLabel ? `<div class="test-environment-banner">${icon('lock')}<div><strong>${esc(previewLabel)}</strong><span>Banco e sessões separados · dados fictícios · e-mails simulados · acesso pelo painel de prévia do Arena</span></div></div>` : ''}${content}</main><footer class="main-footer"><span>Aura © ${new Date().getFullYear()} <span class="footer-sep">•</span> Mais tempo para cuidar.</span><span>${demo ? '<i class="demo-dot"></i> Ambiente de demonstração · dados fictícios' : 'Seu espaço, com mais leveza.'}</span></footer></div>`;
}
function pageHeading(title, subtitle, action = '') { return `<section class="page-heading"><div><h1>${title}</h1><p>${subtitle}</p></div>${action}</section>`; }
const newBooking = () => `<button class="button primary" data-action="book">${icon('plus')}Novo agendamento</button>`;
function monthCalendar() {
  const month = state.calendarMonth, first = new Date(month.getFullYear(), month.getMonth(), 1), last = new Date(month.getFullYear(), month.getMonth() + 1, 0);
  const offset = first.getDay();
  let days = '';
  for (let i = 0; i < Math.ceil((last.getDate() + offset) / 7) * 7; i++) {
    const d = new Date(month.getFullYear(), month.getMonth(), i - offset + 1), key = dateKey(d), outside = d.getMonth() !== month.getMonth();
    const has = state.appointments.some(a => a.appointment_date === key && !['cancelled', 'rejected'].includes(a.status));
    days += `<button class="calendar-day ${outside ? 'muted' : ''} ${key === state.selectedDate ? 'selected' : ''} ${key === today() ? 'today' : ''}" data-action="calendar-day" data-date="${key}" aria-label="${prettyDate(key)}" aria-pressed="${key === state.selectedDate}">${d.getDate()}${has && !outside ? '<i></i>' : ''}</button>`;
  }
  return `<div class="month-navigation"><h3>${esc(month.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' }))}</h3><div><button class="icon-button" data-action="month" data-direction="-1" aria-label="Mês anterior">${icon('chevron', 'flip')}</button><button class="icon-button" data-action="month" data-direction="1" aria-label="Próximo mês">${icon('chevron')}</button></div></div><div class="calendar-week">${['D', 'S', 'T', 'Q', 'Q', 'S', 'S'].map(s => `<span>${s}</span>`).join('')}</div><div class="calendar-grid">${days}</div><div class="calendar-legend"><span><i></i> Com agendamentos</span><button data-action="today">Voltar para hoje</button></div>`;
}
function sparkline(color, seed = 1) {
  const counts = Array.from({ length: 7 }, (_, i) => { const day = dateObj(state.selectedDate); day.setDate(day.getDate() - 6 + i); return state.appointments.filter(a => a.appointment_date === dateKey(day) && (seed !== 2 || a.status === 'confirmed') && (seed !== 3 || a.status === 'pending')).length; });
  const max = Math.max(...counts, 1);
  return `<svg class="sparkline" viewBox="0 0 100 35" aria-hidden="true"><path d="${counts.map((v, i) => `${i ? 'L' : 'M'}${i * 16 + 2},${30 - v / max * 22}`).join(' ')}" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
}
function stats() {
  const daily = state.appointments.filter(a => a.appointment_date === state.selectedDate && !['cancelled', 'rejected'].includes(a.status));
  const revenue = daily.filter(a => a.status === 'completed').reduce((sum, a) => sum + Number(a.price), 0);
  const cards = [
    ['calendar', 'lavender', 'Agendamentos', daily.length.toString().padStart(2, '0'), 'Seu dia em movimento', '#a18bbf', 1],
    ['checkCircle', 'green', 'Confirmados', daily.filter(a => a.status === 'confirmed').length.toString().padStart(2, '0'), 'Tudo certo para receber', '#86b09d', 2],
    ['clock', 'peach', 'Aguardando confirmação', daily.filter(a => a.status === 'pending').length.toString().padStart(2, '0'), 'Um toque de atenção', '#d9ac7e', 3],
    ['money', 'blue', 'Receita do dia', money(revenue), 'De atendimentos concluídos', '#95aac7', 4],
  ];
  return `<div class="stats-grid">${cards.map(([symbol, color, label, value, desc, stroke, seed]) => `<article class="stat-card"><div class="stat-top"><span>${label}</span><span class="stat-icon ${color}">${icon(symbol)}</span></div><div class="stat-value">${value}${sparkline(stroke, seed)}</div><p>${desc}</p></article>`).join('')}</div>`;
}
function filterAppointments(history = false) {
  let list = state.appointments.filter(a => history ? ['completed', 'cancelled', 'rejected'].includes(a.status) : true);
  if (!history && route() !== 'meus-agendamentos') {
    if (state.period === 'day') list = list.filter(a => a.appointment_date === state.selectedDate);
    else { const start = dateObj(state.selectedDate); const end = dateObj(state.selectedDate); end.setDate(end.getDate() + 6); list = list.filter(a => dateObj(a.appointment_date) >= start && dateObj(a.appointment_date) <= end); }
  }
  if (route() === 'meus-agendamentos') list = list.filter(a => ['pending', 'confirmed'].includes(a.status));
  if (state.statusFilter) list = list.filter(a => a.status === state.statusFilter);
  if (state.search) list = list.filter(a => `${a.client_name} ${a.service_name}`.toLowerCase().includes(state.search.toLowerCase()));
  return list;
}
function appointmentTable(list, showDate = false) {
  if (!list.length) return empty('Um espaço para novos momentos', 'Nenhum agendamento encontrado para este período.');
  return `<div class="table-scroll"><table class="appointments-table"><thead><tr><th>HORÁRIO</th>${staff() ? '<th>CLIENTE</th>' : ''}<th>SERVIÇO</th><th>STATUS</th><th class="align-right"><span class="sr-only">Ações</span></th></tr></thead><tbody>${list.map(a => `<tr><td><strong class="time-label">${a.start_time.slice(0, 5)}</strong><small>${showDate ? prettyDate(a.appointment_date, { month: 'short' }) : `${a.duration_minutes} min`}</small></td>${staff() ? `<td><div class="person-cell">${avatar(a.client_name, a.client)}<div><strong>${esc(a.client_name)}</strong><small>${state.clients.find(c => c.id === a.client)?.phone ? formatPhone(state.clients.find(c => c.id === a.client).phone) : 'Cliente Aura'}</small></div></div></td>` : ''}<td><strong class="service-name">${esc(a.service_name)}</strong><small>${money(a.price)}</small></td><td>${statusBadge(a.status)}</td><td><button class="icon-button" data-action="appointment" data-id="${a.id}" aria-label="Detalhes do agendamento de ${esc(a.client_name)}">${icon('more')}</button></td></tr>`).join('')}</tbody></table></div>`;
}
function scheduleCard(full = false, history = false) {
  const list = filterAppointments(history);
  const title = history ? 'Seus atendimentos, em detalhes' : route() === 'meus-agendamentos' ? 'Seus próximos momentos' : 'Agenda do dia';
  return `<section class="card schedule-card"><div class="card-heading"><div><h2>${title}<span class="count-badge">${list.length}</span></h2><p>${history ? 'Um registro de cada cuidado.' : `${state.selectedDate === today() ? 'Hoje, ' : ''}${prettyDate(state.selectedDate, { weekday: 'long' })}`}</p></div>${!history && route() !== 'meus-agendamentos' ? `<div class="segmented"><button data-action="period" data-period="day" class="${state.period === 'day' ? 'active' : ''}">Dia</button><button data-action="period" data-period="week" class="${state.period === 'week' ? 'active' : ''}">Semana</button></div>` : icon('history')}</div><div class="table-toolbar"><label class="input-search">${icon('search')}<input type="search" placeholder="${staff() ? 'Buscar cliente ou serviço…' : 'Buscar serviço…'}" id="appointment-search" value="${esc(state.search)}" aria-label="Buscar agendamentos"></label><select id="status-filter" aria-label="Filtrar status"><option value="">Todos os status</option>${Object.entries(statuses).map(([k, v]) => `<option value="${k}" ${state.statusFilter === k ? 'selected' : ''}>${v}</option>`).join('')}</select></div><div id="appointment-results">${appointmentTable(list, history || state.period === 'week' || route() === 'meus-agendamentos')}</div><div class="table-footer"><span>${list.length ? `${list.length} agendamento${list.length !== 1 ? 's' : ''} ${history ? 'no histórico' : 'neste período'}` : 'Sua agenda, no seu ritmo'}</span>${!full ? '<a href="#agenda">Ver agenda completa ' + icon('arrow') + '</a>' : '<span class="muted-text">Horário de Brasília</span>'}</div></section>`;
}
function dashboard() {
  const firstName = esc(state.settings.professional_name || state.user.name.split(' ')[0]);
  const services = state.services.map(s => ({ ...s, count: state.appointments.filter(a => a.service === s.id && a.status === 'completed').length })).sort((a, b) => b.count - a.count).slice(0, 3);
  return `${pageHeading(`Seu dia, em harmonia<span class="title-dot">.</span>`, `Olá, ${firstName}! Que tal fazer de hoje um dia ainda mais bonito?`, newBooking())}
    <section class="welcome-banner"><div><span class="eyebrow">UM POUCO DE ORGANIZAÇÃO. MUITO MAIS LEVEZA.</span><h2>Você tem o dom de cuidar.<br>Deixe a rotina com a gente.</h2><span class="banner-caption">Seu negócio floresce quando você tem tempo para o que ama.</span></div><span class="banner-mark">aura ✳</span></section>
    ${stats()}<div class="dashboard-grid"><div class="dashboard-main">${scheduleCard()}<section class="card popular-card"><div class="card-heading"><div><h2>Os queridinhos do studio ${icon('heart')}</h2><p>Seus serviços mais realizados</p></div><a href="#servicos" class="text-link">Ver serviços ${icon('arrow')}</a></div><div class="popular-grid">${services.map((s, i) => `<button class="popular-service" data-action="service-detail" data-id="${s.id}"><span class="service-symbol tone-${i}">${icon(i === 1 ? 'spark' : i === 2 ? 'heart' : 'flower')}</span><div><strong>${esc(s.name)}</strong><small>${s.count} atendimento${s.count !== 1 ? 's' : ''}</small></div>${icon('chevron')}</button>`).join('')}</div></section></div>
    <aside class="dashboard-aside"><section class="card mini-calendar">${monthCalendar()}</section><section class="card quick-actions"><div class="card-heading"><h2>Facilite sua rotina</h2>${icon('spark')}</div><button data-action="client-new"><span class="quick-icon lavender">${icon('users')}</span><span><strong>Cadastrar cliente</strong><small>Uma nova conexão começa aqui</small></span>${icon('chevron')}</button><button data-action="block"><span class="quick-icon peach">${icon('lock')}</span><span><strong>Bloquear horário</strong><small>Reserve um tempo para você</small></span>${icon('chevron')}</button><a href="#horarios"><span class="quick-icon green">${icon('clock')}</span><span><strong>Horários de atendimento</strong><small>Sua agenda, do seu jeito</small></span>${icon('chevron')}</a></section><div class="gentle-note">${icon('flower')}<p>Cuidar de você também<br>faz parte do seu negócio.</p><span>um lembrete do Aura ♡</span></div></aside></div>`;
}
function agendaPage(history = false) {
  return `${pageHeading(history ? 'Cada cuidado, uma história.' : staff() ? 'Espaço para bons encontros.' : 'Seu próximo momento de cuidado.', history ? 'Consulte os atendimentos realizados, cancelados e recusados.' : 'Organize seus horários e acompanhe cada agendamento.', history ? '' : newBooking())}
    <div class="${history || !staff() ? 'single-column' : 'agenda-grid'}"><div>${!history && staff() ? `<div class="date-bar"><button class="button secondary small" data-action="date-step" data-direction="-1" aria-label="Dia anterior">${icon('chevron', 'flip')}</button><label><input type="date" id="agenda-date" value="${state.selectedDate}" aria-label="Data da agenda"></label><button class="button secondary small" data-action="date-step" data-direction="1" aria-label="Próximo dia">${icon('chevron')}</button><button class="button secondary small" data-action="today">Hoje</button></div>` : ''}${scheduleCard(true, history)}</div>${!history && staff() ? `<aside><section class="card mini-calendar">${monthCalendar()}</section><section class="card blocks-card"><h2>Horários bloqueados</h2>${state.blocks.filter(b => b.date >= today()).slice(0, 6).map(b => `<div class="block-item"><div><strong>${prettyDate(b.date)}</strong><p>${b.start_time.slice(0, 5)} – ${b.end_time.slice(0, 5)} · ${esc(b.reason || 'Pausa')}</p></div><button class="icon-button" data-action="unblock" data-id="${b.id}" aria-label="Remover bloqueio">${icon('close')}</button></div>`).join('') || '<p class="muted-text">Nenhum bloqueio programado.</p>'}<button class="button secondary full" data-action="block">${icon('lock')}Bloquear horário</button></section></aside>` : ''}</div>`;
}
function formatPhone(phone) { return phone?.length === 11 ? `(${phone.slice(0, 2)}) ${phone.slice(2, 7)}-${phone.slice(7)}` : esc(phone); }
function clientsPage() {
  const list = state.clients.filter(c => `${c.full_name} ${c.email} ${c.phone}`.toLowerCase().includes(state.clientSearch.toLowerCase()));
  return `${pageHeading('Conexões que florescem.', 'Cada cliente é única. Tenha todos os detalhes sempre por perto.', `<button class="button primary" data-action="client-new">${icon('plus')}Nova cliente</button>`)}<div class="mini-metrics"><span>${icon('users')}<strong>${state.clients.filter(c => c.status).length}</strong> clientes ativas</span><span>${icon('heart')}Cuidado que vira relacionamento</span></div><section class="card"><div class="card-heading"><h2>Suas clientes <span class="count-badge">${list.length}</span></h2><label class="input-search">${icon('search')}<input id="client-search" type="search" placeholder="Buscar por nome, e-mail ou telefone" value="${esc(state.clientSearch)}" aria-label="Buscar clientes"></label></div><div class="table-scroll"><table class="clients-table"><thead><tr><th>CLIENTE</th><th>CONTATO</th><th>ATENDIMENTOS</th><th>STATUS</th><th></th></tr></thead><tbody>${list.map(c => `<tr><td><div class="person-cell">${avatar(c.full_name, c.id)}<div><strong>${esc(c.full_name)}</strong><small>Desde ${prettyDate(c.created_at.slice(0, 10), { month: 'short', year: 'numeric' })}</small></div></div></td><td><strong>${formatPhone(c.phone)}</strong><small>${esc(c.email)}</small></td><td><strong>${state.appointments.filter(a => a.client === c.id && a.status === 'completed').length}</strong><small>realizados</small></td><td><span class="status ${c.status ? 'confirmed' : 'cancelled'}"><i></i>${c.status ? 'Ativa' : 'Inativa'}</span></td><td><button class="button secondary small" data-action="client-detail" data-id="${c.id}">Ver perfil ${icon('chevron')}</button></td></tr>`).join('')}</tbody></table>${list.length ? '' : empty('Nenhuma cliente encontrada', 'Tente outro nome ou cadastre uma nova cliente.', 'users')}</div></section>`;
}
function servicesPage() {
  const categories = [...new Set(state.services.map(s => s.category))];
  const list = state.services.filter(s => !state.serviceCategory || s.category === state.serviceCategory);
  return `${pageHeading(staff() ? 'Seu talento, em cada detalhe.' : 'Um cuidado que é só seu.', staff() ? 'Organize seus serviços e valorize o que você faz de melhor.' : 'Escolha o seu próximo momento de beleza e bem-estar.', staff() ? `<button class="button primary" data-action="service-new">${icon('plus')}Novo serviço</button>` : '')}<div class="category-tabs"><button class="${!state.serviceCategory ? 'active' : ''}" data-action="category" data-category="">Todos os serviços <span>${state.services.length}</span></button>${categories.map(c => `<button class="${state.serviceCategory === c ? 'active' : ''}" data-action="category" data-category="${esc(c)}">${esc(c)}</button>`).join('')}</div><div class="services-grid">${list.map((s, i) => `<article class="card service-card"><div class="service-art tone-${i % 4}">${s.image ? `<img src="${esc(s.image)}" alt="${esc(s.name)}" loading="lazy">` : `<span class="art-orbit"></span>${icon(['flower', 'spark', 'heart', 'flower'][i % 4])}<span class="art-caption">${esc(s.category)}</span>`}${!s.status ? '<span class="inactive-badge">Inativo</span>' : ''}<button class="icon-button" data-action="${staff() ? 'service-edit' : 'service-detail'}" data-id="${s.id}" aria-label="${staff() ? 'Editar' : 'Ver'} ${esc(s.name)}">${icon(staff() ? 'edit' : 'arrow')}</button></div><div class="service-content"><span class="eyebrow">${esc(s.category)}</span><h2>${esc(s.name)}</h2><p>${esc(s.description)}</p><div class="service-details"><span>${icon('clock')}${s.duration_minutes} min</span><strong>${money(s.price)}</strong></div><button class="button secondary full" data-action="${staff() ? 'service-detail' : 'book'}" data-id="${s.id}">${staff() ? 'Ver detalhes' : 'Quero agendar'}${icon('arrow')}</button></div></article>`).join('') || empty('Novos cuidados vêm por aí', 'Os serviços estarão disponíveis em breve.', 'flower')}</div>`;
}
function hoursPage() {
  const days = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo'];
  return `${pageHeading('Uma rotina no seu ritmo.', 'Defina quando seu espaço está aberto para receber.')}<div class="settings-grid"><section class="card"><div class="card-heading"><div><h2>Horários de atendimento</h2><p>Toque em um dia para ajustar seus horários e intervalos.</p></div>${icon('clock')}</div><div class="hours-list">${days.map((name, index) => { const h = state.hours.find(h => h.day_of_week === index); return `<button class="hours-row" data-action="hour-edit" data-day="${index}"><span class="day-indicator ${h?.is_available ? 'on' : ''}"></span><strong>${name}</strong><span>${h?.is_available ? `${h.opening_time.slice(0, 5)} – ${h.closing_time.slice(0, 5)}` : 'Fechado'}</span><small>${h?.is_available && h.break_start ? `Pausa ${h.break_start.slice(0, 5)} – ${h.break_end.slice(0, 5)}` : '—'}</small>${icon('edit')}</button>`; }).join('')}</div></section><aside><div class="info-card">${icon('heart')}<h3>Seu tempo também importa.</h3><p>Deixe um respiro entre os atendimentos. Você pode definir o intervalo e o prazo de cancelamento nas configurações.</p><a href="#configuracoes" class="text-link">Ajustar preferências ${icon('arrow')}</a></div><button class="button secondary full" data-action="block">${icon('lock')}Bloquear uma data ou horário</button><p class="hint">Alterações valem para novas reservas. Agendamentos existentes são preservados; revise sua agenda ao mudar o expediente.</p></aside></div>`;
}
function settingsPage() {
  const s = state.settings;
  return `${pageHeading('Do seu jeito. Com a sua essência.', 'Os pequenos ajustes que fazem sua rotina funcionar melhor.')}<div class="settings-grid"><section class="card settings-form"><div class="card-heading"><div><h2>Preferências do studio</h2><p>Informações e regras para os seus agendamentos.</p></div>${icon('settings')}</div><form id="settings-form" class="padded-form">${formError}<div class="form-grid">${field('Nome do studio', 'studio_name', s.studio_name, 'text', 'required maxlength="100"')}${field('Seu nome profissional', 'professional_name', s.professional_name, 'text', 'required maxlength="100"')}${field('Intervalo entre atendimentos (min)', 'interval_minutes', s.interval_minutes, 'number', 'required min="0" max="120"')}${field('Antecedência para cancelar (horas)', 'cancellation_hours', s.cancellation_hours, 'number', 'required min="0" max="720"')}${field('Passo dos horários disponíveis (min)', 'slot_step_minutes', s.slot_step_minutes, 'number', 'required min="5" max="60"')}</div><p class="hint">Cancelamentos e reagendamentos das clientes respeitam o prazo definido. Você, como profissional, pode gerenciar exceções.</p><div class="form-footer"><button type="submit" class="button primary">${icon('check')}Salvar preferências</button></div></form></section><aside class="info-card">${icon('lock')}<h3>Seu espaço está protegido.</h3><p>O Aura utiliza sessões seguras. Cada cliente acessa somente seus próprios agendamentos e dados pessoais.</p><p>Para gerenciar usuários e permissões, utilize o Django Admin no endereço do seu back-end.</p></aside></div>`;
}
function homePage() {
  return `${pageHeading(state.user ? `Que bom ter você aqui, ${esc(state.user.name.split(' ')[0])}.` : 'Sua beleza merece uma pausa.', 'Um espaço de acolhimento, beleza e cuidado. Feito para você.', `<button class="button primary" data-action="book">${icon('calendar')}Agendar meu momento</button>`)}<section class="welcome-banner client-banner"><div><span class="eyebrow">BEM-VINDA AO ${esc(state.settings.studio_name || 'STUDIO AURA').toUpperCase()}</span><h2>O seu tempo de se cuidar<br>começa aqui.</h2><span class="banner-caption">Beleza natural. Atendimento com carinho. Uma experiência sua.</span></div></section><section class="home-benefits">${[['flower', 'Cuidado em cada detalhe', 'Serviços pensados para realçar a sua essência.'], ['calendar', 'No seu melhor horário', 'Agende de onde estiver, com praticidade.'], ['heart', 'Um momento só seu', 'Atendimento individual, acolhedor e especial.']].map(([symbol, title, text]) => `<article>${icon(symbol)}<h3>${title}</h3><p>${text}</p></article>`).join('')}</section><div class="section-heading"><h2>Encontre o seu próximo cuidado</h2><a class="text-link" href="#servicos">Todos os serviços ${icon('arrow')}</a></div><div class="services-grid">${state.services.filter(s => s.status).slice(0, 3).map((s, i) => `<article class="card home-service"><span class="service-symbol tone-${i}">${icon(['flower', 'spark', 'heart'][i])}</span><span class="eyebrow">${esc(s.category)}</span><h2>${esc(s.name)}</h2><p>${esc(s.description)}</p><div class="service-details"><span>${icon('clock')}${s.duration_minutes} min</span><strong>${money(s.price)}</strong></div><button class="button secondary full" data-action="service-detail" data-id="${s.id}">Conhecer o serviço ${icon('arrow')}</button></article>`).join('')}</div>`;
}
function clientFields(c = {}, register = false) {
  return `<div class="form-grid">${field('Nome completo *', 'full_name', c.full_name, 'text', 'required autocomplete="name" maxlength="150"')}${field('E-mail *', 'email', c.email, 'email', 'required autocomplete="email"')}${field('Telefone com DDD *', 'phone', c.phone, 'tel', 'required autocomplete="tel" placeholder="(11) 99999-9999"')}${field('Data de nascimento', 'birth_date', c.birth_date, 'date', `max="${today()}"`)}${field('CPF (opcional)', 'cpf', c.cpf, 'text', 'maxlength="14"')}${field('Endereço (opcional)', 'address', c.address, 'text', 'autocomplete="street-address" maxlength="250"')}${register ? `${field('Senha *', 'password', '', 'password', 'required minlength="8" autocomplete="new-password"')}${field('Confirmar senha *', 'password_confirmation', '', 'password', 'required minlength="8" autocomplete="new-password"')}` : ''}<label class="field full-width"><span>Observações</span><textarea name="notes" rows="3" placeholder="Algo importante para o seu atendimento?">${esc(c.notes || '')}</textarea></label></div>${register ? `<p class="hint">Use pelo menos 8 caracteres. Evite senhas comuns e informações pessoais.</p><label class="checkbox-label"><input type="checkbox" name="terms" required>Li e aceito os <button type="button" class="text-link" data-action="terms">termos de uso e privacidade</button>.</label>` : ''}`;
}
function authPage(kind = 'login') {
  const reset = kind === 'recuperar-senha', confirm = kind === 'redefinir-senha', register = kind === 'cadastro';
  return `<div class="auth-layout ${register ? 'register-layout' : ''}"><div class="auth-story"><span class="eyebrow">BELEZA É SE SENTIR BEM.</span><h1>Um tempo para você.<br>Um cuidado de verdade.</h1><p>Crie conexões, encontre sua melhor versão e floresça no seu ritmo.</p><div class="auth-flower">${icon('flower')}</div><span class="brand-word">aura<span>✳</span></span></div><section class="card auth-card"><span class="auth-symbol">${icon(reset || confirm ? 'lock' : 'flower')}</span><h2>${register ? 'Seu cuidado começa aqui.' : reset ? 'Vamos recuperar seu acesso.' : confirm ? 'Uma nova senha, um novo começo.' : 'Que bom ter você de volta.'}</h2><p>${register ? 'Crie sua conta e reserve seu próximo momento.' : reset ? 'Enviaremos um link para o seu e-mail cadastrado.' : confirm ? 'Escolha uma senha segura para sua conta.' : 'Entre para gerenciar seus momentos de cuidado.'}</p><form id="auth-form" data-kind="${kind}">${formError}${register ? clientFields({}, true) : confirm ? `${field('Nova senha', 'password', '', 'password', 'required minlength="8" autocomplete="new-password"')}${field('Confirmar nova senha', 'password_confirmation', '', 'password', 'required minlength="8" autocomplete="new-password"')}` : `${field('Seu e-mail', 'email', '', 'email', 'required autocomplete="email" placeholder="voce@exemplo.com"')}${!reset ? `${field('Sua senha', 'password', '', 'password', 'required autocomplete="current-password" placeholder="Sua senha de acesso"')}<a class="forgot-link" href="#recuperar-senha">Esqueci minha senha</a>` : ''}`}<button class="button primary full" type="submit">${register ? 'Criar minha conta' : reset ? 'Enviar link de recuperação' : confirm ? 'Salvar nova senha' : 'Entrar no meu espaço'}${icon('arrow')}</button></form><div class="auth-bottom">${register || reset || confirm ? 'Já tem uma conta? <a href="#login">Entrar</a>' : 'Seu primeiro cuidado por aqui? <a href="#cadastro">Criar conta</a>'}</div>${demo && !register ? '<button class="demo-link" data-action="demo-login">Explorar como profissional · demonstração</button>' : ''}</section></div>`;
}
function profilePage() {
  return `${pageHeading('A sua essência, em detalhes.', 'Mantenha seus dados atualizados para um atendimento ainda melhor.')}<section class="card profile-card"><div class="card-heading"><div class="person-cell">${avatar(state.user.name, state.user.id, 'large')}<div><h2>${esc(state.user.name)}</h2><p>Seu perfil no Aura</p></div></div></div><form id="profile-form" class="padded-form">${formError}${clientFields(state.user.profile || {})}<div class="form-footer"><a class="text-link" href="#recuperar-senha">Alterar minha senha</a><button class="button primary" type="submit">${icon('check')}Salvar meus dados</button></div></form></section>`;
}
function render() {
  let page = route(), content;
  const adminRoutes = ['painel', 'agenda', 'clientes', 'horarios', 'configuracoes'];
  if (adminRoutes.includes(page) && !staff()) { location.hash = state.user ? 'inicio' : 'login'; return; }
  if (['meus-agendamentos', 'historico', 'perfil'].includes(page) && !state.user) { location.hash = 'login'; return; }
  if (state.user && ['login', 'cadastro'].includes(page)) { location.hash = staff() ? 'painel' : 'inicio'; return; }
  if (page === 'painel') content = dashboard();
  else if (['agenda', 'meus-agendamentos', 'historico'].includes(page)) content = agendaPage(page === 'historico');
  else if (page === 'clientes') content = clientsPage();
  else if (page === 'servicos') content = servicesPage();
  else if (page === 'horarios') content = hoursPage();
  else if (page === 'configuracoes') content = settingsPage();
  else if (page === 'perfil') content = profilePage();
  else if (['login', 'cadastro', 'recuperar-senha', 'redefinir-senha'].includes(page)) content = authPage(page);
  else content = homePage();
  document.getElementById('app').innerHTML = shell(content);
  document.title = `Aura • ${document.querySelector('.breadcrumb strong')?.textContent || 'Seu espaço de beleza'}`;
}

async function openBooking(serviceId = '', existing = null) {
  if (!state.user) { toast('Entre ou crie uma conta para reservar seu horário.'); location.hash = 'login'; return; }
  const services = state.services.filter(s => s.status);
  if (!services.length) { toast('Nenhum serviço disponível para agendar.', true); return; }
  const date = existing?.appointment_date || (state.selectedDate < today() ? today() : state.selectedDate);
  modal(existing ? 'Um novo horário para você.' : 'Um novo momento de cuidado.', existing ? 'Escolha outro horário. O agendamento voltará para confirmação.' : 'Escolha o serviço, encontre um horário e deixe o resto com a gente.', `<form id="booking-form" data-id="${existing?.id || ''}" class="padded-form">${formError}<div class="booking-steps"><span class="active">1 <b>Serviço e cliente</b></span><i></i><span class="active">2 <b>Seu horário</b></span></div><div class="form-grid"><label class="field ${!staff() ? 'full-width' : ''}"><span>Serviço *</span><select name="service" id="booking-service" required><option value="">Selecione um serviço</option>${services.map(s => `<option value="${s.id}" ${String(existing?.service || serviceId) === String(s.id) ? 'selected' : ''}>${esc(s.name)} · ${money(s.price)}</option>`).join('')}</select></label>${staff() ? `<label class="field"><span>Cliente *</span><select name="client" required><option value="">Selecione uma cliente</option>${state.clients.filter(c => c.status).map(c => `<option value="${c.id}" ${existing?.client === c.id ? 'selected' : ''}>${esc(c.full_name)}</option>`).join('')}</select></label>` : ''}${field('Data do atendimento *', 'appointment_date', date, 'date', `id="booking-date" required min="${today()}"`)}<div class="booking-summary" id="booking-summary">${icon('flower')}<span>Um cuidado feito para você</span></div></div><div class="slots-section"><label>Horários disponíveis <span>Horário de Brasília</span></label><div id="booking-slots" class="slots-grid"><p class="hint">Escolha um serviço para consultar os horários.</p></div><input type="hidden" name="start_time" required></div><label class="field"><span>Observações (opcional)</span><textarea name="client_notes" rows="2" placeholder="Quer nos contar algo sobre o atendimento?">${esc(existing?.client_notes || '')}</textarea></label><p class="booking-policy">${icon('help')}Cancelamento ou reagendamento com ${state.settings.cancellation_hours}h de antecedência.</p>${submitButton(existing ? 'Solicitar reagendamento' : 'Criar agendamento')}</form>`, true);
  if (serviceId || existing) await updateSlots();
}
let slotsVersion = 0;
async function updateSlots() {
  const serviceId = document.getElementById('booking-service')?.value, day = document.getElementById('booking-date')?.value;
  const node = document.getElementById('booking-slots');
  if (!node) return;
  const version = ++slotsVersion;
  const input = document.querySelector('[name=start_time]'); if (input) input.value = '';
  if (!serviceId || !day) { node.innerHTML = '<p class="hint">Escolha um serviço e uma data.</p>'; return; }
  const service = state.services.find(s => s.id === Number(serviceId));
  document.getElementById('booking-summary').innerHTML = `${icon('clock')}<span>${service.duration_minutes} minutos <strong>${money(service.price)}</strong></span>`;
  node.innerHTML = '<p class="hint">Encontrando um horário para você…</p>';
  try {
    const result = await api(`/available-slots/?date=${encodeURIComponent(day)}&service_id=${serviceId}`);
    if (version !== slotsVersion || !node.isConnected) return;
    node.innerHTML = result.slots.length ? result.slots.map(slot => `<button type="button" class="time-slot" data-action="slot" data-time="${slot.start_time}">${slot.start_time}</button>`).join('') : '<div class="slots-empty">Nenhum horário disponível nesta data. Que tal escolher outro dia?</div>';
  } catch (e) { if (version === slotsVersion && node.isConnected) node.innerHTML = `<p class="form-error">${esc(e.message)}</p>`; }
}
function appointmentDetail(id) {
  const a = state.appointments.find(a => a.id === id); if (!a) return;
  const active = ['pending', 'confirmed'].includes(a.status);
  modal('Os detalhes do seu cuidado.', `Agendamento #${String(a.id).padStart(4, '0')}`, `<div class="padded-form"><div class="appointment-person">${avatar(a.client_name, a.client, 'large')}<div><h3>${esc(a.client_name)}</h3><p>${esc(a.service_name)}</p></div>${statusBadge(a.status)}</div><div class="detail-grid"><div><span>Data</span><strong>${prettyDate(a.appointment_date, { year: 'numeric' })}</strong></div><div><span>Horário</span><strong>${a.start_time.slice(0, 5)} – ${a.end_time.slice(0, 5)}</strong></div><div><span>Duração</span><strong>${a.duration_minutes} minutos</strong></div><div><span>Valor reservado</span><strong>${money(a.price)}</strong></div></div>${a.client_notes ? `<div class="detail-note"><strong>Observações da cliente</strong><p>${esc(a.client_notes)}</p></div>` : ''}${staff() && a.admin_notes ? `<div class="detail-note"><strong>Observações internas</strong><p>${esc(a.admin_notes)}</p></div>` : ''}<div class="appointment-actions">${staff() && a.status === 'pending' ? `<button class="button primary" data-action="transition" data-id="${a.id}" data-target="confirm">${icon('check')}Confirmar</button><button class="button secondary" data-action="transition" data-id="${a.id}" data-target="reject">Recusar</button>` : ''}${staff() && a.status === 'confirmed' ? `<button class="button primary" data-action="transition" data-id="${a.id}" data-target="complete">${icon('checkCircle')}Concluir atendimento</button>` : ''}${active ? `<button class="button secondary" data-action="reschedule" data-id="${a.id}">${icon('calendar')}Reagendar</button><button class="button danger" data-action="cancel-confirm" data-id="${a.id}">Cancelar agendamento</button>` : ''}</div></div>`);
}
function serviceForm(id) {
  const s = state.services.find(s => s.id === id) || {};
  modal(id ? 'Seu serviço, com a sua essência.' : 'Um novo cuidado no studio.', 'Conte os detalhes do serviço que você oferece.', `<form id="service-form" data-id="${id || ''}" class="padded-form">${formError}<div class="form-grid">${field('Nome do serviço *', 'name', s.name, 'text', 'required maxlength="120"')}${field('Categoria *', 'category', s.category, 'text', 'required maxlength="80" list="categories"')}<datalist id="categories">${[...new Set(state.services.map(s => s.category))].map(c => `<option value="${esc(c)}">`).join('')}</datalist>${field('Duração (minutos) *', 'duration_minutes', s.duration_minutes || 30, 'number', 'required min="5" max="480"')}${field('Preço (R$) *', 'price', s.price || '', 'number', 'required min="0" step="0.01"')}<label class="field full-width"><span>Descrição</span><textarea name="description" rows="3">${esc(s.description || '')}</textarea></label><div class="full-width">${field('URL da imagem (opcional)', 'image', s.image, 'url', 'placeholder="https://…"')}</div></div><label class="checkbox-label"><input type="checkbox" name="status" ${s.status !== false ? 'checked' : ''}>Serviço ativo e disponível para agendamento</label>${submitButton(id ? 'Salvar serviço' : 'Cadastrar serviço')}</form>`);
}
function serviceDetail(id) {
  const s = state.services.find(s => s.id === id); if (!s) return;
  modal(s.name, s.category, `<div class="padded-form"><div class="service-detail-art tone-0">${icon('flower')}</div><p class="service-description">${esc(s.description)}</p><div class="detail-grid"><div><span>Duração do cuidado</span><strong>${s.duration_minutes} minutos</strong></div><div><span>Investimento</span><strong>${money(s.price)}</strong></div></div><div class="form-footer">${staff() ? `<button class="button secondary" data-action="service-edit" data-id="${id}">${icon('edit')}Editar serviço</button>` : ''}<button class="button primary" data-action="book" data-id="${id}" ${!s.status ? 'disabled' : ''}>${icon('calendar')}${s.status ? 'Agendar este cuidado' : 'Serviço inativo'}</button></div></div>`);
}
function clientForm(id) {
  const c = state.clients.find(c => c.id === id) || {};
  modal(id ? 'Um perfil sempre atualizado.' : 'Uma nova conexão começa aqui.', 'Clientes cadastradas por você podem criar uma senha por recuperação de acesso.', `<form id="client-form" data-id="${id || ''}" class="padded-form">${formError}${clientFields(c)}${id ? `<label class="checkbox-label"><input type="checkbox" name="status" ${c.status ? 'checked' : ''}>Cliente ativa para novos agendamentos</label>` : ''}${submitButton(id ? 'Salvar cliente' : 'Cadastrar cliente')}</form>`, true);
}
function clientDetail(id) {
  const c = state.clients.find(c => c.id === id); if (!c) return;
  const appointments = state.appointments.filter(a => a.client === id).slice().reverse();
  modal(c.full_name, 'Cada detalhe ajuda você a cuidar melhor.', `<div class="padded-form"><div class="profile-overview">${avatar(c.full_name, c.id, 'large')}<div><strong>${esc(c.email)}</strong><p>${formatPhone(c.phone)}</p></div><button class="button secondary small" data-action="client-edit" data-id="${id}">${icon('edit')}Editar</button></div><div class="detail-grid"><div><span>Aniversário</span><strong>${c.birth_date ? prettyDate(c.birth_date) : 'Não informado'}</strong></div><div><span>Endereço</span><strong>${esc(c.address || 'Não informado')}</strong></div></div>${c.notes ? `<div class="detail-note"><strong>Observações</strong><p>${esc(c.notes)}</p></div>` : ''}<h3 class="history-title">Histórico de agendamentos</h3><div class="client-history">${appointments.map(a => `<button data-action="appointment" data-id="${a.id}"><span><strong>${esc(a.service_name)}</strong><small>${prettyDate(a.appointment_date)} · ${a.start_time.slice(0, 5)}</small></span>${statusBadge(a.status)}</button>`).join('') || '<p class="muted-text">O primeiro cuidado ainda está por vir.</p>'}</div>${c.status ? `<div class="form-footer"><button class="button danger small" data-action="deactivate-client" data-id="${id}">Desativar cliente e acesso</button></div>` : ''}</div>`, true);
}
function blockForm() {
  modal('Uma pausa também faz bem.', 'Reserve um horário para você. Atendimentos existentes precisam ser remarcados antes.', `<form id="block-form" class="padded-form">${formError}${field('Data *', 'date', state.selectedDate < today() ? today() : state.selectedDate, 'date', `required min="${today()}"`)}<div class="form-grid">${field('Início *', 'start_time', '09:00', 'time', 'required')}${field('Fim *', 'end_time', '18:00', 'time', 'required')}</div>${field('Motivo (opcional)', 'reason', '', 'text', 'placeholder="Ex.: compromisso pessoal" maxlength="200"')}${submitButton('Bloquear horário')}</form>`);
}
function hourForm(day) {
  const h = state.hours.find(h => h.day_of_week === day) || {};
  modal('O ritmo do seu atendimento.', ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo'][day], `<form id="hour-form" data-id="${h.id || ''}" data-day="${day}" class="padded-form">${formError}<label class="checkbox-label"><input type="checkbox" name="is_available" ${h.is_available !== false ? 'checked' : ''}>Aberto para atendimento neste dia</label><div class="form-grid">${field('Abertura *', 'opening_time', h.opening_time?.slice(0, 5) || '09:00', 'time', 'required')}${field('Fechamento *', 'closing_time', h.closing_time?.slice(0, 5) || '18:00', 'time', 'required')}${field('Início do intervalo', 'break_start', h.break_start?.slice(0, 5), 'time')}${field('Fim do intervalo', 'break_end', h.break_end?.slice(0, 5), 'time')}</div><p class="hint">Preencha os dois campos de intervalo ou deixe ambos vazios. Agendamentos existentes não serão alterados.</p>${submitButton()}</form>`);
}
function helpModal() {
  modal('Uma rotina mais leve começa aqui.', 'O essencial para você aproveitar seu Aura.', `<div class="padded-form help-content">${[['calendar', 'Organize seus encontros', 'Crie um agendamento, escolha o serviço e consulte os horários livres. O Aura considera a duração, as pausas e os bloqueios.'], ['users', 'Cultive suas conexões', 'Cadastre clientes, atualize seus contatos e acompanhe o histórico de cada cuidado.'], ['clock', 'Respeite o seu tempo', 'Defina os dias de atendimento, os intervalos e o prazo de cancelamento. Reserve pausas na sua agenda.'], ['lock', 'Tenha seu próprio espaço', 'Clientes acessam apenas seus dados. A profissional gerencia o studio. Para recuperar o acesso, use “Esqueci minha senha”.']].map(([i, t, d]) => `<article>${icon(i)}<div><h3>${t}</h3><p>${d}</p></div></article>`).join('')}<div class="info-strip">${demo ? 'Você está em uma demonstração com dados fictícios. As alterações feitas aqui são salvas neste ambiente de teste.' : 'Precisa mudar uma reserva fora do prazo? Entre em contato diretamente com o studio.'}</div></div>`);
}

async function handleAction(button, event) {
  const action = button.dataset.action, id = Number(button.dataset.id);
  if (action === 'reload-preview') { location.reload(); return; }
  if (action === 'close-modal' || action === 'backdrop' && event.target === button) closeModal();
  else if (action === 'menu') document.querySelector('.sidebar').classList.toggle('open');
  else if (action === 'book') { closeModal(); await openBooking(id || ''); }
  else if (action === 'calendar-day') { state.selectedDate = button.dataset.date; state.calendarMonth = dateObj(state.selectedDate); render(); }
  else if (action === 'month') { state.calendarMonth = new Date(state.calendarMonth.getFullYear(), state.calendarMonth.getMonth() + Number(button.dataset.direction), 1); render(); }
  else if (action === 'today') { state.selectedDate = today(); state.calendarMonth = dateObj(today()); render(); }
  else if (action === 'date-step') { const day = dateObj(state.selectedDate); day.setDate(day.getDate() + Number(button.dataset.direction)); state.selectedDate = dateKey(day); state.calendarMonth = day; render(); }
  else if (action === 'period') { state.period = button.dataset.period; render(); }
  else if (action === 'category') { state.serviceCategory = button.dataset.category; render(); }
  else if (action === 'service-new' || action === 'service-edit') serviceForm(id);
  else if (action === 'service-detail') serviceDetail(id);
  else if (action === 'client-new' || action === 'client-edit') clientForm(id);
  else if (action === 'client-detail') clientDetail(id);
  else if (action === 'appointment') appointmentDetail(id);
  else if (action === 'hour-edit') hourForm(Number(button.dataset.day));
  else if (action === 'block') blockForm();
  else if (action === 'slot') { document.querySelectorAll('.time-slot').forEach(b => b.classList.remove('selected')); button.classList.add('selected'); document.querySelector('[name=start_time]').value = button.dataset.time; }
  else if (action === 'reschedule') await openBooking('', state.appointments.find(a => a.id === id));
  else if (action === 'cancel-confirm') modal('Cancelar este momento?', 'O horário ficará disponível para outras clientes.', `<div class="padded-form"><p>Você pode agendar novamente quando quiser, conforme a disponibilidade do studio.</p><div class="form-footer"><button class="button secondary" data-action="appointment" data-id="${id}">Manter agendamento</button><button class="button danger" data-action="transition" data-id="${id}" data-target="cancel">Sim, cancelar</button></div></div>`);
  else if (action === 'transition') {
    button.disabled = true;
    await api(`/appointments/${id}/${button.dataset.target}/`, 'POST', {});
    closeModal(); await refresh(); toast('Agendamento atualizado com sucesso.');
  } else if (action === 'unblock') {
    await api(`/blocked-slots/${id}/`, 'DELETE'); await refresh(); toast('Horário desbloqueado.');
  } else if (action === 'deactivate-client') {
    modal('Desativar esta cliente?', 'O histórico será preservado, mas o acesso à conta será desativado.', `<div class="padded-form"><p>Agendamentos existentes continuam na agenda. Gerencie-os antes de desativar o acesso, se necessário.</p><div class="form-footer"><button class="button secondary" data-action="client-detail" data-id="${id}">Voltar</button><button class="button danger" data-action="deactivate-confirm" data-id="${id}">Desativar acesso</button></div></div>`);
  } else if (action === 'deactivate-confirm') {
    await api(`/clients/${id}/`, 'DELETE'); closeModal(); await refresh(); toast('Cliente desativada. Histórico preservado.');
  } else if (action === 'help') helpModal();
  else if (action === 'account') {
    modal('Seu espaço no Aura.', state.user.email, `<div class="padded-form"><div class="account-options">${!staff() ? `<a class="button secondary" href="#perfil" data-action="close-modal">${icon('users')}Meu perfil</a>` : '<a href="#configuracoes" data-action="close-modal" class="button secondary">' + icon('settings') + 'Preferências do studio</a>'}<button class="button danger" data-action="logout">${icon('logout')}Sair da minha conta</button></div>${demo ? '<p class="hint">Ambiente de demonstração. Você pode sair e criar uma conta de cliente para experimentar os dois perfis.</p>' : ''}</div>`);
  } else if (action === 'logout') {
    await api('/auth/logout/', 'POST', {}); state.user = null; closeModal(); await loadData(); location.hash = 'login'; render(); toast('Você saiu com segurança. Até logo!');
  } else if (action === 'demo-login') {
    state.user = await api('/demo-login/', 'POST', {}); await loadData(); location.hash = 'painel'; render(); toast('Bem-vinda à demonstração do Aura.');
  } else if (action === 'notifications') {
    modal('Novidades no seu espaço.', 'Acompanhe o que acontece com seus agendamentos.', `<div class="notification-list">${state.notifications.map(n => `<article class="${n.read ? '' : 'unread'}">${icon('bell')}<div><p>${esc(n.message)}</p><small>${new Date(n.created_at).toLocaleString('pt-BR')}</small></div></article>`).join('') || empty('Tudo em dia por aqui', 'Suas novidades aparecerão neste espaço.', 'bell')}</div>`);
    await api('/notifications/read_all/', 'POST', {}); state.notifications.forEach(n => n.read = true); document.querySelector('.notification-button i')?.remove();
  } else if (action === 'search') {
    modal('O que você procura?', 'Encontre clientes, serviços ou atalhos do seu espaço.', `<div class="padded-form"><label class="input-search global-search">${icon('search')}<input id="global-search" type="search" placeholder="Comece a digitar…" autocomplete="off" aria-label="Busca global"></label><div id="global-results"><div class="search-shortcuts"><a href="#servicos" data-action="close-modal">${icon('flower')}Explorar serviços${icon('arrow')}</a>${state.user ? `<a href="#${staff() ? 'agenda' : 'meus-agendamentos'}" data-action="close-modal">${icon('calendar')}Abrir minha agenda${icon('arrow')}</a>` : ''}</div></div></div>`);
  } else if (action === 'terms') {
    // Preserve the registration form and its inputs while the policy is visible.
    const form = document.getElementById('auth-form');
    if (form?.querySelector('.terms-content')) { form.querySelector('.terms-content').remove(); return; }
    const policy = document.createElement('div'); policy.className = 'terms-content info-strip';
    policy.textContent = `Seus dados são utilizados pelo studio para identificar sua conta, organizar os atendimentos e comunicar alterações. CPF, nascimento e endereço são opcionais. Nunca compartilhe sua senha. Cancelamentos e reagendamentos exigem ${state.settings.cancellation_hours} horas de antecedência. Para solicitar acesso, correção ou exclusão dos seus dados, entre em contato com a profissional. Registros necessários podem ser preservados conforme obrigações legais. O studio é responsável pelo atendimento e pelo tratamento dos dados. Esta política deve ser revisada e complementada com identificação e contato do controlador antes da publicação com clientes reais.`;
    form?.querySelector('.checkbox-label')?.after(policy);
  }
}
document.addEventListener('click', event => {
  const button = event.target.closest('[data-action]'); if (!button) return;
  handleAction(button, event).catch(e => { if (button.isConnected) button.disabled = false; toast(e.message, true); });
});
document.addEventListener('change', async event => {
  const node = event.target;
  try {
    if (['booking-service', 'booking-date'].includes(node.id)) await updateSlots();
    else if (node.id === 'status-filter') { state.statusFilter = node.value; render(); }
    else if (node.id === 'agenda-date' && node.value) { state.selectedDate = node.value; state.calendarMonth = dateObj(node.value); render(); }
  } catch (e) { toast(e.message, true); }
});
document.addEventListener('input', event => {
  const node = event.target;
  if (node.id === 'appointment-search') {
    state.search = node.value;
    document.getElementById('appointment-results').innerHTML = appointmentTable(filterAppointments(route() === 'historico'), route() === 'historico' || state.period === 'week' || route() === 'meus-agendamentos');
  } else if (node.id === 'client-search') {
    const pos = node.selectionStart; state.clientSearch = node.value; render(); const input = document.getElementById('client-search'); input.focus(); input.setSelectionRange(pos, pos);
  } else if (node.id === 'global-search') {
    const q = node.value.trim().toLowerCase();
    const services = state.services.filter(s => s.name.toLowerCase().includes(q));
    const clients = state.clients.filter(c => `${c.full_name} ${c.email}`.toLowerCase().includes(q));
    document.getElementById('global-results').innerHTML = q ? `<div class="search-results">${[...services.map(s => `<button data-action="service-detail" data-id="${s.id}">${icon('flower')}<span><strong>${esc(s.name)}</strong><small>Serviço · ${money(s.price)}</small></span>${icon('chevron')}</button>`), ...clients.map(c => `<button data-action="client-detail" data-id="${c.id}">${avatar(c.full_name, c.id)}<span><strong>${esc(c.full_name)}</strong><small>Cliente · ${esc(c.email)}</small></span>${icon('chevron')}</button>`)].join('') || empty('Nenhum resultado', 'Tente buscar por outro nome.', 'search')}</div>` : '<p class="hint">Digite o nome de um serviço ou cliente.</p>';
  }
});
document.addEventListener('keydown', event => {
  if ((event.metaKey || event.ctrlKey) && event.key === 'k') { event.preventDefault(); document.querySelector('[data-action=search]')?.click(); }
  if (event.key === 'Escape') closeModal();
  if (event.key === 'Tab' && document.querySelector('.modal')) {
    const focusables = [...document.querySelectorAll('.modal a, .modal button:not([disabled]), .modal input:not([type=hidden]), .modal select, .modal textarea')].filter(el => el.offsetParent !== null);
    const first = focusables[0], last = focusables.at(-1);
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
  }
});
document.addEventListener('submit', async event => {
  const form = event.target; if (!form.id.endsWith('-form')) return;
  event.preventDefault();
  const data = Object.fromEntries(new FormData(form)), id = form.dataset.id;
  const button = form.querySelector('[type=submit]'), errorBox = form.querySelector('.form-error');
  const previous = button.innerHTML; button.disabled = true; button.innerHTML = 'Um instante…'; errorBox.hidden = true;
  try {
    if (form.id === 'auth-form') {
      const kind = form.dataset.kind;
      if (kind === 'recuperar-senha') {
        const result = await api('/auth/password-reset/', 'POST', data);
        form.innerHTML = `<div class="success-message">${icon('mail')}<h3>Confira sua caixa de entrada.</h3><p>${esc(result.detail)}</p><a class="button secondary full" href="#login">Voltar para o login</a></div>`; return;
      }
      if (kind === 'redefinir-senha') {
        const params = new URLSearchParams(location.hash.split('?')[1] || '');
        await api('/auth/password-reset-confirm/', 'POST', { ...data, uid: params.get('uid'), token: params.get('token') });
        location.hash = 'login'; toast('Senha atualizada. Entre com sua nova senha.'); return;
      }
      if (kind === 'cadastro') { data.terms = data.terms === 'on'; data.birth_date ||= null; }
      state.user = await api(`/auth/${kind === 'cadastro' ? 'register' : 'login'}/`, 'POST', data);
      await loadData(); location.hash = staff() ? 'painel' : 'inicio'; render(); toast('Bem-vinda ao seu espaço!');
    } else if (form.id === 'booking-form') {
      if (!data.start_time) throw new Error('Escolha um dos horários disponíveis.');
      data.service = Number(data.service); if (staff()) data.client = Number(data.client);
      const result = await api(`/appointments/${id ? id + '/' : ''}`, id ? 'PATCH' : 'POST', data);
      await refresh();
      modal(id ? 'Seu novo horário está reservado.' : 'Um encontro com o seu bem-estar.', 'Solicitação de agendamento recebida!', `<div class="confirmation padded-form"><div class="confirmation-icon">${icon('check')}</div><h2>${id ? 'Reagendamento solicitado!' : 'Tudo pronto para o seu cuidado!'}</h2><p>Aguarde a confirmação da profissional. Você pode acompanhar tudo pela sua agenda.</p><div class="confirmation-summary"><strong>${esc(result.service_name)}</strong><span>${prettyDate(result.appointment_date)} · ${result.start_time.slice(0, 5)}</span><span>${money(result.price)} · ${statusBadge('pending')}</span></div><button class="button primary full" data-action="close-modal">Perfeito, combinado! ${icon('check')}</button></div>`);
    } else if (form.id === 'service-form') {
      data.status = form.elements.status.checked;
      await api(`/services/${id ? id + '/' : ''}`, id ? 'PATCH' : 'POST', data); closeModal(); await refresh(); toast(id ? 'Serviço atualizado.' : 'Novo serviço cadastrado!');
    } else if (form.id === 'client-form') {
      data.birth_date ||= null; if (id) data.status = form.elements.status.checked;
      await api(`/clients/${id ? id + '/' : ''}`, id ? 'PATCH' : 'POST', data); closeModal(); await refresh(); toast(id ? 'Dados da cliente atualizados.' : 'Uma nova cliente no seu espaço!');
    } else if (form.id === 'profile-form') {
      data.birth_date ||= null; state.user = await api('/auth/me/', 'PATCH', data); render(); toast('Seus dados foram atualizados.');
    } else if (form.id === 'block-form') {
      await api('/blocked-slots/', 'POST', data); closeModal(); await refresh(); toast('Pausa reservada na sua agenda.');
    } else if (form.id === 'hour-form') {
      data.day_of_week = Number(form.dataset.day); data.is_available = form.elements.is_available.checked;
      data.break_start ||= null; data.break_end ||= null;
      await api(`/business-hours/${id ? id + '/' : ''}`, id ? 'PATCH' : 'POST', data); closeModal(); await refresh(); toast('Horários de atendimento atualizados.');
    } else if (form.id === 'settings-form') {
      await api('/settings/', 'PATCH', data); await refresh(); toast('Suas preferências foram salvas.');
    }
  } catch (e) {
    errorBox.innerHTML = `<span>${esc(e.message)}</span>${cookieHelp(e)}`; errorBox.hidden = false; errorBox.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  } finally { if (button.isConnected) { button.disabled = false; button.innerHTML = previous; } }
});
window.addEventListener('hashchange', () => { closeModal(); state.search = ''; state.statusFilter = ''; render(); window.scrollTo(0, 0); });
async function init() {
  const startPage = window.AURA_CONFIG?.START_PAGE;
  if (!location.hash && startPage === 'login') history.replaceState(null, '', '#login');
  try {
    await api('/auth/csrf/');
    try { state.user = await api('/auth/me/'); }
    catch (e) {
      if (e.status !== 403 && e.status !== 401) throw e;
      if (demo && !location.hash) state.user = await api('/demo-login/', 'POST', {});
    }
    await loadData();
    if (demo && staff() && !state.appointments.some(a => a.appointment_date === today())) {
      const next = state.appointments.find(a => a.appointment_date > today());
      if (next) { state.selectedDate = next.appointment_date; state.calendarMonth = dateObj(next.appointment_date); }
    }
    state.loading = false; render();
  } catch (e) {
    document.getElementById('app').innerHTML = `<div class="boot"><span class="brand-word">aura<span>✳</span></span><h2>Seu espaço estará aqui.</h2><p>${esc(e.message)}</p>${cookieHelp(e)}<button class="button primary" id="retry-connection">Tentar novamente ${icon('arrow')}</button><a href="#login" id="offline-login" class="text-link">Ver tela de acesso</a></div>`;
    document.getElementById('retry-connection').onclick = init;
    document.getElementById('offline-login').onclick = () => { state.user = null; render(); };
  }
}
init();
