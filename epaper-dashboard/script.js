(function () {
  "use strict";

  var API_BASE = window.DASHBOARD_API_BASE || "http://localhost:8646";
  var REFRESH_MS = 30000;
  var MAX_FOOTER_ITEMS = 2;

  // DEFAULT DATA (used if API unavailable):
  const DASHBOARD_DATA = {
    weather: {
      location: "北京", temperature: "27°C", summary: "多云转晴",
      feelsLike: "29°C", rainChance: "10%", wind: "东南 3 级", aqi: "42",
    },
    todos: [
      { text: "刑诉·基本原则+管辖", tag: "HIGH", done: false },
      { text: "行政法·行政许可", tag: "WORK", done: false },
      { text: "商法·公司治理", tag: "WORK", done: true },
      { text: "回复微信消息", tag: "DM", done: false },
      { text: "晚间散步 20 分钟", tag: "LIFE", done: false },
      { text: "复盘明日计划", tag: "PM", done: false },
    ],
    schedule: [
      { time: "10:00-12:00", title: "商法·补网课/复习", note: "商法", done: true },
      { time: "12:00-13:00", title: "午饭", note: "休息", done: true },
      { time: "13:00-14:00", title: "午睡", note: "休息", done: true },
      { time: "14:00-16:00", title: "商法·补网课/复习", note: "商法", done: true },
      { time: "16:00-17:00", title: "吉他练习", note: "休息", done: true },
      { time: "17:00-18:00", title: "晚餐", note: "休息", done: true },
      { time: "18:00-20:00", title: "刑诉·开荒", note: "刑诉", done: true },
      { time: "20:00-21:00", title: "吉他练习", note: "休息", done: true },
      { time: "21:00-22:00", title: "行政法·开荒", note: "行政法", done: true },
      { time: "22:00-23:00", title: "词汇·每日积累", note: "词汇", done: true },
      { time: "23:00-00:00", title: "太极20min+复盘", note: "休息", done: false },
    ],
    focus: { mode: "FOCUS MODE", text: "保持电量", sub: "今日还有 4 个重点块" },
    date: { day: "03", weekday: "星期三", year: "2026", month: "06" },
    updated: "08:30",
  };

  var apiState = {
    plan: null,
    ddl: null,
    lastUpdated: "",
    hasAnyApiData: false
  };

  var els = {};
  var QUOTES = [
    "月色与雪色之间，你是第三种绝色。",
    "你来人间一趟，你要看看太阳。",
    "吹灭读书灯，一身都是月。",
    "你是我在这人间，最想见的风光。",
    "世间万物论沧桑，你在心上。",
    "我曾踏月而来，只因你在山中。",
    "晓看天色暮看云，行也思君，坐也思君。",
    "你是无意穿堂风，偏偏孤倨引山洪。",
    "山中何事？松花酿酒，春水煎茶。",
    "花店不开了，花继续开。",
    "日落跌进昭昭星野，人间忽晚。",
    "你是我眼里的星辰，足矣照亮山河。",
    "若你决定灿烂，山无遮，海无拦。",
    "心中有丘壑，眉目作山河。",
    "愿你千山暮雪，海棠依旧。",
    "且将新火试新茶，诗酒趁年华。",
    "一星陨落，黯淡不了星空灿烂。",
    "这世界有那么多人，多幸运我有个我们。",
    "你闪闪发光，而我努力跟上。",
    "生活原本沉闷，但跑起来就有风。",
    "你风尘仆仆走向我，胜过所有遥远的温柔。",
    "错过了落日余晖，还可以静待满天星辰。",
    "温柔半两，从容一生。",
    "满目山河空念远，不如怜取眼前人。",
    "我见众生皆草木，唯你是青山。",
    "这路遥马急的人间，你我平安喜乐就好。",
    "你遥遥远去，如晚星落尽。",
    "人海茫茫，终有一人，跨越山海奔向。",
    "这个星球偶尔脆弱，而我也偶尔想与你沉没。",
    "你是所有的心动和欢呼雀跃。",
    "一起等月亮爬上来。",
  ];


  document.addEventListener("DOMContentLoaded", function () {
    els = {
      dateDay: document.getElementById("date-day"),
      dateWeekday: document.getElementById("date-weekday"),
      dateYear: document.getElementById("date-year"),
      dateMonth: document.getElementById("date-month"),
      updatedTime: document.getElementById("updated-time"),
      weatherLocation: document.getElementById("weather-location"),
      weatherTemp: document.getElementById("weather-temp"),
      weatherSummary: document.getElementById("weather-summary"),
      weatherFeels: document.getElementById("weather-feels"),
      weatherRain: document.getElementById("weather-rain"),
      weatherWind: document.getElementById("weather-wind"),
      weatherAqi: document.getElementById("weather-aqi"),
      scheduleList: document.getElementById("schedule-list"),
      focusMode: document.getElementById("focus-mode"),
      focusText: document.getElementById("focus-text"),
      focusSub: document.getElementById("focus-sub"),
      dailyQuote: document.getElementById("daily-quote"),
      examStrip: document.getElementById("exam-strip")
    };

    render();
    refreshData();
    window.setInterval(refreshData, REFRESH_MS);
  });

  function apiUrl(path) {
    return new URL(path, API_BASE).toString();
  }

  function fetchJson(path) {
    return fetch(apiUrl(path), { cache: "no-store" }).then(function (response) {
      if (!response.ok) {
        throw new Error(path + " returned " + response.status);
      }
      return response.json();
    });
  }

  function refreshData() {
    return Promise.allSettled([
      fetchJson("/dashboard/plan/list"),
      fetchJson("/dashboard/ddl/list")
    ]).then(function (results) {
      var received = false;

      if (results[0].status === "fulfilled" && results[0].value) {
        apiState.plan = results[0].value;
        received = true;
      }

      if (results[1].status === "fulfilled" && results[1].value) {
        apiState.ddl = results[1].value;
        received = true;
      }

      if (received) {
        apiState.hasAnyApiData = true;
        apiState.lastUpdated = formatClock(new Date());
      }

      render();
    });
  }

  function render() {
    var data = buildDashboardData();

    renderDate(data.date);
    renderQuote();
    renderWeather(data.weather);
    renderSchedule(data.schedule);
    renderFocus(data.focus, data.exams);
    renderUpdated(data.updated);
  }

  function renderQuote() {
    var idx = new Date().getDate() % QUOTES.length;
    els.dailyQuote.textContent = QUOTES[idx];
  }

  function buildDashboardData() {
    var data = clone(DASHBOARD_DATA);
    data.exams = [];
    data.ddl = [];

    if (apiState.plan) {
      var mapped = mapPlan(apiState.plan);
      data.schedule = mapped.schedule;
      data.exams = mapped.exams;

      if (mapped.date) {
        data.date = mapped.date;
      }
    }

    if (apiState.ddl) {
      data.ddl = normalizeDdlItems(apiState.ddl.items);
      data.ddl.forEach(function (item) {
        data.schedule.push({
          time: "",
          title: item.label,
          tag: "DDL",
          note: item.name,
          done: false
        });
      });
    }

    var openCount = data.schedule.filter(function (item) {
      return !item.done;
    }).length;
    data.focus.sub = "今日还有 " + openCount + " 个重点块";

    data.updated = apiState.hasAnyApiData && apiState.lastUpdated
      ? apiState.lastUpdated
      : DASHBOARD_DATA.updated;

    return data;
  }

  function mapPlan(plan) {
    var items = Array.isArray(plan.items) ? plan.items : [];
    var schedule = [];

    items.forEach(function (item, idx) {
      var task = cleanText(item.task, "未命名事项");
      var time = cleanText(item.time, "");
      var done = Boolean(item.done);
      var isBreak = Boolean(item.break);

      schedule.push({
        time: time,
        title: task,
        tag: cleanTag(item.subject || item.task),
        note: scheduleNote(item, done, isBreak),
        done: done,
        _planIndex: idx
      });
    });

    return {
      schedule: schedule,
      exams: normalizeExams(plan.exams),
      date: dateFromText(plan.date)
    };
  }

  function scheduleNote(item, done, isBreak) {
    if (done) {
      return "已完成";
    }
    if (isBreak) {
      return "休息 / 恢复";
    }
    return cleanText(item.note, "计划块");
  }

  function normalizeDdlItems(items) {
    if (!Array.isArray(items)) {
      return [];
    }

    return items.map(function (item) {
      var days = toNumber(item.days_left);
      var name = cleanText(item.name, "未命名 DDL");
      return {
        name: name,
        daysLeft: days,
        label: name + " " + formatDays(days)
      };
    }).sort(function (a, b) {
      var left = a.daysLeft === null ? 9999 : a.daysLeft;
      var right = b.daysLeft === null ? 9999 : b.daysLeft;
      return left - right;
    });
  }

  function normalizeExams(exams) {
    if (!Array.isArray(exams)) {
      return [];
    }

    return exams.map(function (exam) {
      return {
        name: cleanText(exam.name, "未命名考试"),
        daysLeft: toNumber(exam.days_left)
      };
    }).sort(function (a, b) {
      var left = a.daysLeft === null ? 9999 : a.daysLeft;
      var right = b.daysLeft === null ? 9999 : b.daysLeft;
      return left - right;
    });
  }

  function renderDate(date) {
    els.dateDay.textContent = cleanText(date.day, "02");
    els.dateWeekday.textContent = cleanText(date.weekday, "星期二");
    els.dateYear.textContent = cleanText(date.year, "2026");
    els.dateMonth.textContent = cleanText(date.month, "06");
  }

  function renderWeather(weather) {
    els.weatherLocation.textContent = cleanText(weather.location, "北京");
    els.weatherTemp.textContent = cleanText(weather.temperature, "27°C");
    els.weatherSummary.textContent = cleanText(weather.summary, "多云转晴");
    els.weatherFeels.textContent = cleanText(weather.feelsLike, "29°C");
    els.weatherRain.textContent = cleanText(weather.rainChance, "10%");
    els.weatherWind.textContent = cleanText(weather.wind, "东南 3 级");
    els.weatherAqi.textContent = cleanText(weather.aqi, "42");
  }

  function renderSchedule(schedule) {
    var rows = Array.isArray(schedule) ? schedule : [];
    els.scheduleList.innerHTML = "";

    if (!rows.length) {
      els.scheduleList.appendChild(emptyState("暂无安排"));
      return;
    }

    rows.forEach(function (item) {
      var row = document.createElement("div");
      row.className = "schedule-item"
        + (item.done ? " is-done" : "")
        + (item.time ? "" : " no-time");

      if (item.time) {
        var time = document.createElement("time");
        time.className = "schedule-time";
        time.textContent = item.time;
        row.appendChild(time);
      }

      var box = document.createElement("div");
      box.className = "schedule-box";

      var title = document.createElement("div");
      title.className = "schedule-title";
      title.textContent = cleanText(item.title, "未命名安排");

      var note = document.createElement("div");
      note.className = "schedule-note";
      if (item.tag && item.tag !== "MISC") {
        note.textContent = item.tag;
      } else {
        note.textContent = cleanText(item.note, "");
      }

      box.appendChild(title);
      box.appendChild(note);
      row.appendChild(box);

      // Click to toggle done for plan items
      if (item._planIndex !== undefined && item._planIndex >= 0) {
        row.style.cursor = "pointer";
        row.onclick = (function (idx) {
          return function () {
            fetch(apiUrl("/dashboard/plan/tick"), {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ index: idx }),
            }).then(function () { refreshData(); });
          };
        })(item._planIndex);
      }

      els.scheduleList.appendChild(row);
    });
  }

  function renderFocus(focus, exams) {
    els.focusMode.textContent = cleanText(focus.mode, "FOCUS MODE");
    els.focusText.textContent = cleanText(focus.text, "保持电量");
    els.focusSub.textContent = cleanText(focus.sub, "今日还有 4 个重点块");
    els.examStrip.textContent = footerLine("考试", exams);
  }

  function renderUpdated(updated) {
    var value = cleanText(updated, "08:30");
    els.updatedTime.textContent = value;
    els.updatedTime.setAttribute("datetime", value);
  }

  function footerLine(prefix, items) {
    var rows = Array.isArray(items) ? items.slice(0, MAX_FOOTER_ITEMS) : [];
    if (!rows.length) {
      return prefix + " 暂无";
    }

    return prefix + " " + rows.map(function (item) {
      return cleanText(item.name, "未命名") + " " + formatDays(item.daysLeft);
    }).join(" / ");
  }


  function emptyState(text) {
    var node = document.createElement("div");
    node.className = "empty-state";
    node.textContent = text;
    return node;
  }

  function dateFromText(value) {
    var text = cleanText(value, "");
    var match = text.match(/^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$/);
    if (!match) {
      return null;
    }

    var year = Number(match[1]);
    var month = Number(match[2]);
    var day = Number(match[3]);
    var date = new Date(year, month - 1, day);

    if (!year || !month || !day || Number.isNaN(date.getTime())) {
      return null;
    }

    var weekdays = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"];
    return {
      day: pad2(day),
      weekday: weekdays[date.getDay()],
      year: String(year),
      month: pad2(month)
    };
  }

  function formatClock(date) {
    return pad2(date.getHours()) + ":" + pad2(date.getMinutes());
  }

  function formatDays(days) {
    if (days === null || days === undefined) {
      return "D--";
    }
    if (days < 0) {
      return "D+" + Math.abs(days);
    }
    return "D-" + days;
  }

  function pad2(value) {
    return String(value).padStart(2, "0");
  }

  function cleanText(value, fallback) {
    if (value === null || value === undefined) {
      return fallback;
    }
    var text = String(value).replace(/\s+/g, " ").trim();
    return text || fallback;
  }

  function cleanTag(value) {
    return cleanText(value, "TASK").replace(/[^0-9A-Za-z]/g, "").slice(0, 5).toUpperCase() || "TASK";
  }

  function toNumber(value) {
    var number = Number(value);
    return Number.isFinite(number) ? number : null;
  }

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }
}());
