let originalData = [];
let filteredData = [];

let currentSort = {
    column: null,
    direction: null
};

let valueFilterType = null;
let daysFilterType = null;

// فیلتر روز مخصوص تب اسپرد
let spreadDaysFilterType = null;

let spreadOriginalData = [];

let spreadCurrentSort = {
    column: null,
    direction: null
};

// ردیف انتخاب‌شده در هر جدول
const selectedRowKeys = {
    market: null,
    spread: null,
    spreadCalculation: null
};

// اطلاعات جدول محاسبات اسپرد
let spreadCalculationOriginalData = [];

// داده‌ای که همین لحظه در جدول نمایش داده می‌شود.
// وجود این متغیر باعث می‌شود هنگام مخفی‌کردن ستون، سورت جدول از بین نرود.
let spreadCalculationCurrentData = [];

let spreadCalculationSort = {
    column: null,
    direction: null
};

// ستون‌هایی که کاربر تیک آن‌ها را برداشته است
const hiddenSpreadCalculationColumns = new Set();

const stockTableColumns = [
    { key: "symbol", label: "نماد", type: "text", width: 190 },
    { key: "company", label: "نام شرکت", type: "text", width: 220 },
    { key: "industry", label: "صنعت", type: "text", width: 220 },
    { key: "market_value", label: "ارزش بازار", unit: "همت", type: "number", format: "marketValue", width: 120 },
    { key: "last_price", label: "آخرین قیمت", unit: "ریال", type: "number", format: "price", percentKey: "last_price_change_percent", width: 125 },
    { key: "closing_price", label: "قیمت پایانی", unit: "ریال", type: "number", format: "price", percentKey: "closing_price_change_percent", width: 125 },
    { key: "trade_value", label: "ارزش معاملات", unit: "میلیارد تومان", type: "number", format: "tradeValue", width: 145 },
    { key: "trade_to_float_percent", label: "نسبت معامله به شناوری", unit: "درصد", type: "number", format: "precisePercent", width: 160 },
    { key: "real_money_flow", label: "ورود پول حقیقی", unit: "میلیارد تومان", type: "number", format: "tradeValue", width: 145 },
    { key: "real_buy_per_capita", label: "سرانه خرید حقیقی", unit: "میلیون تومان", type: "number", format: "perCapita", width: 145 },
    { key: "real_sell_per_capita", label: "سرانه فروش حقیقی", unit: "میلیون تومان", type: "number", format: "perCapita", width: 145 },
    { key: "real_buy_power", label: "قدرت خرید حقیقی", unit: "برابر", type: "number", format: "ratio", width: 140 },
    { key: "trade_volume", label: "حجم معاملات", unit: "میلیون", type: "number", format: "million", width: 125 },
    { key: "share_count", label: "تعداد سهام", unit: "میلیارد", type: "number", format: "billion", width: 125 },
    { key: "floating_share_percent", label: "درصد سهام شناور", type: "number", format: "percent", width: 145 },
    { key: "real_buy_volume", label: "حجم خرید حقیقی", unit: "میلیون", type: "number", format: "million", width: 130 },
    { key: "real_buy_count", label: "تعداد خریدار حقیقی", type: "number", format: "integer", width: 155 },
    { key: "legal_buy_volume", label: "حجم خرید حقوقی", unit: "میلیون", type: "number", format: "million", width: 130 },
    { key: "legal_buy_count", label: "تعداد خریدار حقوقی", type: "number", format: "integer", width: 155 },
    { key: "real_sell_volume", label: "حجم فروش حقیقی", unit: "میلیون", type: "number", format: "million", width: 130 },
    { key: "real_sell_count", label: "تعداد فروشنده حقیقی", type: "number", format: "integer", width: 165 },
    { key: "legal_sell_volume", label: "حجم فروش حقوقی", unit: "میلیون", type: "number", format: "million", width: 130 },
    { key: "legal_sell_count", label: "تعداد فروشنده حقوقی", type: "number", format: "integer", width: 165 },
    { key: "monthly_average_volume", label: "میانگین حجم ماه", unit: "میلیون", type: "number", format: "million", width: 135 },
    { key: "order_book_buy_value", label: "مجموع ارزش سفارش‌ها", side: "خرید", sideKey: "buy", unit: "میلیارد تومان", type: "number", format: "tradeValue", width: 160 },
    { key: "order_book_buy_volume", label: "مجموع حجم سفارش‌ها", side: "خرید", sideKey: "buy", unit: "میلیون", type: "number", format: "million", width: 150 },
    { key: "order_book_buy_count", label: "مجموع تعداد سفارش‌ها", side: "خرید", sideKey: "buy", type: "number", format: "integer", width: 150 },
    { key: "order_book_sell_value", label: "مجموع ارزش سفارش‌ها", side: "فروش", sideKey: "sell", unit: "میلیارد تومان", type: "number", format: "tradeValue", width: 160 },
    { key: "order_book_sell_volume", label: "مجموع حجم سفارش‌ها", side: "فروش", sideKey: "sell", unit: "میلیون", type: "number", format: "million", width: 150 },
    { key: "order_book_sell_count", label: "مجموع تعداد سفارش‌ها", side: "فروش", sideKey: "sell", type: "number", format: "integer", width: 150 }
];

const dollarConvertibleStockColumns = new Set([
    "trade_value",
    "real_money_flow"
]);

let stockCatalogRows = [];
let stockCatalogLoaded = false;
let stockCatalogLoading = false;
const defaultStockTableSort = { key: "market_value", direction: "desc" };
let stockTableSort = { ...defaultStockTableSort };
let stockSortInteractionStarted = false;
let stockGroupByIndustry = false;
let stockMarketFilter = { min: null, max: null };
let stockSearchQuery = "";
let stockIndustryQuery = "";
let stockTradeValueInUsd = false;
let stockRefreshPollTimer = null;
let stockAutoRefreshTimer = null;
const hiddenStockColumns = new Set();

let stockWatchlistRows = [];
let stockWatchlistLoaded = false;
let stockWatchlistLoading = false;
let stockWatchlistSearchQuery = "";
let stockWatchlistGroupByIndustry = false;
let stockWatchlistTradeValueInUsd = false;
let stockWatchlistSort = { key: null, direction: null };
let stockWatchlistSortInteractionStarted = false;
let stockWatchlistAutoRefreshTimer = null;
const hiddenStockWatchlistColumns = new Set();

let stockStrategyLoaded = false;
let stockStrategyLoading = false;
let stockStrategyAutoRefreshTimer = null;

const DASHBOARD_AUTO_REFRESH_INTERVAL = 2 * 60_000;
const STOCK_REFRESH_POLL_INTERVAL = 1_500;
const STOCK_AUTO_REFRESH_INTERVAL = DASHBOARD_AUTO_REFRESH_INTERVAL;

let watchMarketData = {
    times: [],
    charts: {},
    overview: { prices: [], flows: [], errors: [] },
    errors: []
};
let watchMarketLoaded = false;
let watchMarketLoading = false;
let watchMarketAutoRefreshTimer = null;
const watchMarketClockFormatter = new Intl.DateTimeFormat("en-GB", {
    timeZone: "UTC",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23"
});
const watchMarketNumberFormatter = new Intl.NumberFormat("fa-IR", {
    maximumFractionDigits: 1
});
const watchMarketSignedFormatter = new Intl.NumberFormat("fa-IR", {
    maximumFractionDigits: 1,
    signDisplay: "exceptZero"
});

// =====================================================
// AUTO REFRESH
// =====================================================

const AUTO_REFRESH_INTERVAL = 30_000;

let marketAutoRefreshRunning = false;
let spreadAutoRefreshRunning = false;

let marketAutoRefreshTimer = null;
let spreadAutoRefreshTimer = null;

function normalizeSymbol(value) {
    return String(value ?? "")
        .trim()
        .replace(/[يى]/g, "ی")
        .replace(/ك/g, "ک")
        .replace(/[\s\u200c\u200f\ufeff]+/g, "");
}

const rawMapping = {
    "طوتعاون":"وتعاون","طهمن":"خبهمن","طهرم":"اهرم","طموج":"موج",
    "طملي":"فملی","طملت":"وبملت","طمخا":"اخابر","طكاريس":"کاریس","طفلا":"فولاد",
    "طفصبا":"فصبا","طفزر":"فزر","طفرابورس":"فرابورس","ططعام":"طعام","طصاد":"وبصادر",
    "طشنا":"شپنا","طستر":"خگستر","طسپا":"خساپا","طسامان":"سامان","طرويين":"رویین",
    "طران":"خودران","طذوب":"ذوب","طخود":"خودرو","طخاور":"خاور","طجهش":"جهش",
    "طجار":"وتجارت","طتيام":"تیام","طتوان":"توان","طتاص":"تاصیکو","طتاب":"شتاب",
    "طپناه":"پناه","طپتروآبان":"پتروآبان","طپادا":"پادا","طبيد":"بیدار",
    "طبساما":"بساما","طامين شهر":"امین شهر","طاطلس":"اطلس","طاساس":"آساس",
    "ضوتعاون":"وتعاون","ضهمن":"خبهمن","ضهرم":"اهرم","ضنارنج":"نارنج","ضموج":"موج",
    "ضملي":"فملی","ضملت":"وبملت","ضمخا":"اخابر","ضكاريس":"کاریس","ضفلا":"فولاد",
    "ضفصبا":"فصبا","ضفزر":"فزر","ضفرابورس":"فرابورس","ضطعام":"طعام","ضصاد":"وبصادر",
    "ضشنا":"شپنا","ضستر":"خگستر","ضستا":"شستا","طستا":"شستا","ضسپا":"خساپا","ضسامان":"سامان",
    "ضرويين":"رویین","ضران":"خودران","ضذوب":"ذوب","ضخود":"خودرو","ضخاور":"خاور",
    "ضجهش":"جهش","ضجار":"وتجارت","ضتيام":"تیام","ضتوان":"توان","ضتاص":"تاصیکو",
    "ضتاب":"شتاب","ضپناه":"پناه","ضپتروآبان":"پتروآبان","ضپادا":"پادا",
    "ضبيد":"بیدار","ضبساما":"بساما","ضامين شهر":"امین شهر","ضاطلس":"اطلس",
    "ضاساس":"آساس",
    "ضجوا":"جوانه کوچک","طجوا":"جوانه کوچک",
    "ضراز":"هم تراز","طراز":"هم تراز"
};

const mapping = Object.fromEntries(
    Object.entries(rawMapping).map(([optionSymbol, baseSymbol]) => [
        normalizeSymbol(optionSymbol),
        normalizeSymbol(baseSymbol)
    ])
);

let discoveredBaseSymbols = [];
let marketExpectationsData = null;
let marketExpectationsLoading = false;
let marketExpectationsRefreshTimer = null;
let expectationDetailRows = [];
let expectationDetailSort = { key: null, direction: "asc" };

async function loadData() {

    try {

        /*
            فقط checkbox داخل تب market
        */
        const dataSourceSelect =
            document.getElementById("market-data-source");


        if (!dataSourceSelect) {

            throw new Error(
                "انتخاب‌گر منبع اطلاعات تب مارکت پیدا نشد."
            );
        }


        const dataSourceMode = dataSourceSelect.dataset.value || "live";


        console.log(
            "Market data source:",
            dataSourceMode
        );


        const parameters =
            new URLSearchParams();


        parameters.set(
            "data_source",
            dataSourceMode
        );


        /*
            جلوگیری از Cache
        */
        parameters.set(
            "_ts",
            Date.now().toString()
        );


        /*
            تا قبل از دریافت کامل،
            جدول قبلی باقی می‌ماند.
        */
        const response =
            await fetch(
                `/data?${parameters.toString()}`,
                {
                    cache: "no-store"
                }
            );


        const result =
            await response.json();


        if (!response.ok) {

            throw new Error(
                result.error ||
                `HTTP Error: ${response.status}`
            );
        }


        if (!Array.isArray(result)) {

            throw new Error(
                "داده دریافتی بازار نامعتبر است."
            );
        }


        /*
            بررسی منبع ارزش معاملات
        */
        const firstReturnedRow =
            result.find(row => row);


        /*
            جایگزینی یک‌مرحله‌ای داده
        */
        originalData =
            result;


        /*
            ساخت Header
        */
        const tableHead =
            document.querySelector(
                "#table thead"
            );


        if (
            tableHead &&
            result.length > 0
        ) {

            const headers =
                Object
                    .keys(result[0])
                    .filter(header =>
                        !header.startsWith("__")
                    );


            let headRow = "<tr>";


            headers.forEach(header => {

                headRow += `
                    <th onclick="sortTable('${header}')">
                        ${header}
                    </th>
                `;
            });


            headRow += "</tr>";


            tableHead.innerHTML =
                headRow;
        }


        /*
            اعمال فیلترهای فعلی روی داده جدید
        */
        if (hasActiveFilters()) {

            applyFilters();

        } else {

            filteredData = [
                ...originalData
            ];

            renderTable(
                filteredData
            );
        }


    } catch (error) {

        /*
            در خطا جدول قبلی باقی می‌ماند.
        */
        console.error(
            "Market load error:",
            error
        );
    }
}

function renderTable(data) {

    const tableBody = document.querySelector(
        "#table tbody"
    );

    if (!tableBody) {
        return;
    }

    tableBody.innerHTML = "";

    if (!Array.isArray(data) || data.length === 0) {

        tableBody.innerHTML = `
            <tr>
                <td colspan="20">
                    اطلاعاتی برای نمایش وجود ندارد.
                </td>
            </tr>
        `;

        return;
    }

    const rowsToRender =
        sortRowsByState(
            data,
            currentSort
        );

    const headers = Object
        .keys(data[0])
        .filter(header =>
            !header.startsWith("__")
        );
    rowsToRender.forEach((row, index) => {

        const tr = document.createElement("tr");

        const rowKey = getTableRowKey(
            "market",
            row,
            index
        );

        applyRowSelection({
            tableName: "market",
            tableSelector: "#table",
            rowElement: tr,
            rowKey
        });

        headers.forEach(header => {

            const td = document.createElement("td");

            td.classList.add("number-cell");
            td.textContent = row[header] ?? "";

            tr.appendChild(td);
        });

        tableBody.appendChild(tr);
    });
}

// ================= SORT =================
function sortTable(column) {

    if (currentSort.column !== column) {
        currentSort = { column: column, direction: "desc" }; // 👈 تغییر اینجا
    } else if (currentSort.direction === "desc") {
        currentSort.direction = "asc";
    } else {
        currentSort = { column: null, direction: null };
        renderTable(filteredData);
        return;
    }

    let sorted = [...filteredData];

    sorted.sort((a, b) => {
        let valA = a[column];
        let valB = b[column];

        if (typeof valA === "string") valA = valA.replace(/,/g, "");
        if (typeof valB === "string") valB = valB.replace(/,/g, "");

        valA = isNaN(valA) ? valA : Number(valA);
        valB = isNaN(valB) ? valB : Number(valB);

        if (valA < valB) return currentSort.direction === "asc" ? -1 : 1;
        if (valA > valB) return currentSort.direction === "asc" ? 1 : -1;
        return 0;
    });

    renderTable(sorted);
}

// ================= FILTER =================
function applyFilters() {
    
    const baseSymbolFilters = getSelectedValues(
        "filter-base-symbol"
    );
    let symbol = document.getElementById("filter-symbol").value.trim();
    let status = getSingleDropdownValue("filter-status").trim();

    let value = document.getElementById("filter-value").value;

    let days = document.getElementById("filter-days").value;

    filteredData = originalData.filter(row => {

        // --- فیلتر نماد پایه (هوشمند) ---
        if (baseSymbolFilters.length > 0) {

            const optionSymbol =
                row["نماد اختیار"] ?? "";

            const cleanSymbol = normalizeSymbol(
                optionSymbol.replace(/\d+/g, "")
            );

            const base =
                mapping[cleanSymbol] || "";

            if (!baseSymbolFilters.map(normalizeSymbol).includes(base)) {
                return false;
            }
        }

        // --- نماد ---
        if (symbol && !row["نماد اختیار"]?.includes(symbol)) {
            return false;
        }

        // --- وضعیت ---
        if (status && row["وضعیت"] !== status) {
            return false;
        }

        // --- ارزش معاملات ---
        if (value && valueFilterType) {

            let inputValue = Number(value) * 1000000;

            let v = row["ارزش معاملات"]
                ? Number(row["ارزش معاملات"].replace(/,/g, ""))
                : 0;

            if (valueFilterType === "gt" && !(v >= inputValue)) return false;
            if (valueFilterType === "lt" && !(v <= inputValue)) return false;
        }
        // --- روز باقی‌مانده ---
        if (days && daysFilterType) {

            let d = Number(row["روز باقی‌مانده"]) || 0;

            if (daysFilterType === "gt" && !(d >= Number(days))) return false;
            if (daysFilterType === "lt" && !(d <= Number(days))) return false;

            if (daysFilterType === "gte" && !(d >= Number(days))) return false;
            if (daysFilterType === "lte" && !(d <= Number(days))) return false;
            if (daysFilterType === "eq" && !(d === Number(days))) return false;
        }

        return true;
    });

    renderTable(filteredData);
}

// ================= RESET =================
function resetFilters() {

    valueFilterType = null;
    daysFilterType = null;

    document.getElementById("value-up")?.classList.remove("active");
    document.getElementById("value-down")?.classList.remove("active");
    document.getElementById("days-up")?.classList.remove("active");
    document.getElementById("days-down")?.classList.remove("active");

    clearMultiSelect("filter-base-symbol");
    document.getElementById("filter-symbol").value = "";
    setSingleDropdownValue("filter-status", "");
    document.getElementById("filter-value").value = "";
    document.getElementById("filter-days").value = "";

    filteredData = originalData;

    renderTable(filteredData);
}


function hasActiveFilters() {

    return (
        getSelectedValues(
            "filter-base-symbol"
        ).length > 0 ||

        document
            .getElementById("filter-symbol")
            ?.value ||

        document
            .getElementById("filter-status")
            ?.dataset.value ||

        document
            .getElementById("filter-value")
            ?.value ||

        document
            .getElementById("filter-days")
            ?.value
    );
}

function getSelectedValues(dropdownId) {

    const dropdown = document.getElementById(
        dropdownId
    );

    if (!dropdown) {
        return [];
    }

    return Array.from(
        dropdown.querySelectorAll(
            '.check-dropdown-option input[type="checkbox"]:checked'
        )
    ).map(checkbox => checkbox.value);
}


function updateCheckDropdownLabel(dropdown) {

    if (!dropdown) {
        return;
    }

    const selectedValues = getSelectedValues(
        dropdown.id
    );

    const label = dropdown.querySelector(
        ".check-dropdown-label"
    );

    const placeholder =
        dropdown.dataset.placeholder ||
        "انتخاب نماد";

    if (!label) {
        return;
    }

    if (selectedValues.length === 0) {

        label.textContent = placeholder;

        dropdown.classList.remove(
            "has-selection"
        );

    } else if (selectedValues.length <= 2) {

        label.textContent =
            selectedValues.join("، ");

        dropdown.classList.add(
            "has-selection"
        );

    } else {

        label.textContent =
            `${selectedValues.length} نماد انتخاب شد`;

        dropdown.classList.add(
            "has-selection"
        );
    }
}


function clearMultiSelect(dropdownId) {

    const dropdown = document.getElementById(
        dropdownId
    );

    if (!dropdown) {
        return;
    }

    dropdown
        .querySelectorAll(
            '.check-dropdown-option input[type="checkbox"]'
        )
        .forEach(checkbox => {
            checkbox.checked = false;
        });

    updateCheckDropdownLabel(dropdown);
}


function closeAllCheckDropdowns(
    exceptDropdown = null
) {

    document
        .querySelectorAll(".check-dropdown.open")
        .forEach(dropdown => {

            if (dropdown === exceptDropdown) {
                return;
            }

            dropdown.classList.remove("open");

            const toggle = dropdown.querySelector(
                ".check-dropdown-toggle"
            );

            toggle?.setAttribute(
                "aria-expanded",
                "false"
            );
        });
}


function initializeCheckDropdown(dropdown) {

    if (
        !dropdown ||
        dropdown.dataset.initialized === "true"
    ) {
        return;
    }

    const toggle = dropdown.querySelector(
        ".check-dropdown-toggle"
    );

    const menu = dropdown.querySelector(
        ".check-dropdown-menu"
    );

    if (!toggle || !menu) {
        return;
    }

    toggle.addEventListener(
        "click",
        function (event) {

            event.stopPropagation();

            const willOpen =
                !dropdown.classList.contains("open");

            closeAllCheckDropdowns(dropdown);

            dropdown.classList.toggle(
                "open",
                willOpen
            );

            toggle.setAttribute(
                "aria-expanded",
                String(willOpen)
            );
        }
    );

    /*
        کلیک داخل منو باعث بسته‌شدن
        dropdown نمی‌شود.
    */
    menu.addEventListener(
        "click",
        function (event) {
            event.stopPropagation();
        }
    );

    dropdown.dataset.initialized = "true";

    /*
        listenerهای عمومی فقط یک بار
        به document اضافه می‌شوند.
    */
    if (!window.checkDropdownEventsInitialized) {

        document.addEventListener(
            "click",
            function () {
                closeAllCheckDropdowns();
            }
        );

        document.addEventListener(
            "keydown",
            function (event) {

                if (event.key === "Escape") {
                    closeAllCheckDropdowns();
                }
            }
        );

        window.checkDropdownEventsInitialized = true;
    }
}


function populateBaseSymbolDropdown() {

    const baseSymbols = [
        ...Object.values(mapping),
        ...discoveredBaseSymbols
    ];

    const uniqueSymbols = [
        ...new Set(baseSymbols)
    ].sort((firstSymbol, secondSymbol) => {

        return firstSymbol.localeCompare(
            secondSymbol,
            "fa"
        );
    });

    const dropdownIds = [
        "filter-base-symbol",
        "spread-base-symbol"
    ];

    dropdownIds.forEach(dropdownId => {

        const dropdown = document.getElementById(
            dropdownId
        );

        if (!dropdown) {
            return;
        }

        const menu = dropdown.querySelector(
            ".check-dropdown-menu"
        );

        if (!menu) {
            return;
        }

        menu.innerHTML = "";

        uniqueSymbols.forEach(symbol => {

            const optionLabel =
                document.createElement("label");

            optionLabel.className =
                "check-dropdown-option";

            const checkbox =
                document.createElement("input");

            checkbox.type = "checkbox";
            checkbox.value = symbol;

            const optionText =
                document.createElement("span");

            optionText.textContent = symbol;

            checkbox.addEventListener(
                "change",
                function () {
                    updateCheckDropdownLabel(
                        dropdown
                    );
                }
            );

            optionLabel.appendChild(checkbox);
            optionLabel.appendChild(optionText);

            menu.appendChild(optionLabel);
        });

        initializeCheckDropdown(dropdown);
        updateCheckDropdownLabel(dropdown);
    });
}

function setValueFilter(type) {
    valueFilterType = type;

    document.getElementById("value-up")?.classList.remove("active");
    document.getElementById("value-down")?.classList.remove("active");

    document.getElementById(type === "gt" ? "value-up" : "value-down")
        ?.classList.add("active");
}

function setDaysFilter(type) {
    daysFilterType = type;

    document.getElementById("days-up")?.classList.remove("active");
    document.getElementById("days-down")?.classList.remove("active");

    document.getElementById(type === "gt" ? "days-up" : "days-down")
        ?.classList.add("active");
}

function setSpreadDaysFilter(type) {

    spreadDaysFilterType = type;

    const buttons = [
        "days-up-spread",
        "days-down-spread",
        "days-equal-spread"
    ];

    buttons.forEach(id => {
        document
            .getElementById(id)
            ?.classList.remove("active");
    });

    const activeButtonMap = {
        gte: "days-up-spread",
        lte: "days-down-spread",
        eq: "days-equal-spread"
    };

    document
        .getElementById(activeButtonMap[type])
        ?.classList.add("active");
}

function escapeHtml(value) {

    return String(value ?? "").replace(
        /[&<>"']/g,
        character => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#039;"
        })[character]
    );
}

function getTableRowKey(tableName, row, index) {

    if (tableName === "market") {
        return String(
            row["نماد اختیار"] ??
            `market-${index}`
        );
    }

    if (tableName === "spread") {
        return String(
            row["نماد اختیار"] ??
            `spread-${index}`
        );
    }

    if (tableName === "spreadCalculation") {
        return [
            row["خرید"] ?? "",
            row["فروش"] ?? ""
        ].join("|");
    }

    return String(index);
}


function selectTableRow(
    tableName,
    tableSelector,
    rowElement,
    rowKey
) {

    selectedRowKeys[tableName] = rowKey;

    document
        .querySelectorAll(`${tableSelector} tbody tr`)
        .forEach(tr => {
            tr.classList.remove("selected-row");
        });

    rowElement.classList.add("selected-row");
}


function applyRowSelection({
    tableName,
    tableSelector,
    rowElement,
    rowKey
}) {

    rowElement.dataset.rowKey = rowKey;

    if (selectedRowKeys[tableName] === rowKey) {
        rowElement.classList.add("selected-row");
    }

    rowElement.addEventListener("click", function () {
        selectTableRow(
            tableName,
            tableSelector,
            rowElement,
            rowKey
        );
    });
}

function renderSpreadTable(data) {

    const tableHead = document.querySelector(
        "#spread-table thead"
    );

    const tableBody = document.querySelector(
        "#spread-table tbody"
    );

    if (!tableHead || !tableBody) {
        return;
    }

    tableHead.innerHTML = "";
    tableBody.innerHTML = "";

    if (!Array.isArray(data) || data.length === 0) {

        tableBody.innerHTML = `
            <tr>
                <td>
                    نمادی مطابق فیلترهای انتخاب‌شده پیدا نشد
                </td>
            </tr>
        `;

        return;
    }

    const rowsToRender =
        sortRowsByState(
            data,
            spreadCurrentSort
        );

    // دریافت سرستون‌ها از کلیدهای داده
    const headers = Object
        .keys(data[0])
        .filter(header =>
            !header.startsWith("__")
        );

    // ساخت سرستون‌ها
    const headRow = document.createElement("tr");

    headers.forEach(header => {

        const th = document.createElement("th");

        let sortIcon = "";

        if (spreadCurrentSort.column === header) {

            if (spreadCurrentSort.direction === "desc") {
                sortIcon = " ▼";
            }

            if (spreadCurrentSort.direction === "asc") {
                sortIcon = " ▲";
            }
        }

        th.textContent = header + sortIcon;

        th.addEventListener("click", function () {
            sortSpreadTable(header);
        });

        headRow.appendChild(th);
    });

    tableHead.appendChild(headRow);

    // ساخت ردیف‌های جدول
    rowsToRender.forEach((row, index) => {

        const tr = document.createElement("tr");

        const rowKey = getTableRowKey(
            "spread",
            row,
            index
        );

        applyRowSelection({
            tableName: "spread",
            tableSelector: "#spread-table",
            rowElement: tr,
            rowKey
        });

        headers.forEach(header => {

            const td = document.createElement("td");

            td.classList.add("number-cell");
            td.textContent = row[header] ?? "";

            tr.appendChild(td);
        });

        tableBody.appendChild(tr);
    });
}

function sortSpreadTable(column) {

    // اگر روی ستون جدید کلیک شده باشد، ابتدا نزولی مرتب می‌شود
    if (spreadCurrentSort.column !== column) {

        spreadCurrentSort = {
            column: column,
            direction: "desc"
        };

    } else if (spreadCurrentSort.direction === "desc") {

        // کلیک دوم: صعودی
        spreadCurrentSort.direction = "asc";

    } else {

        // کلیک سوم: بازگشت به ترتیب اولیه
        spreadCurrentSort = {
            column: null,
            direction: null
        };

        renderSpreadTable(spreadOriginalData);
        return;
    }

    const sortedData = [...spreadOriginalData];

    sortedData.sort((a, b) => {

        let valueA = normalizeSpreadSortValue(a[column]);
        let valueB = normalizeSpreadSortValue(b[column]);

        if (valueA < valueB) {
            return spreadCurrentSort.direction === "asc" ? -1 : 1;
        }

        if (valueA > valueB) {
            return spreadCurrentSort.direction === "asc" ? 1 : -1;
        }

        return 0;
    });

    renderSpreadTable(sortedData);
}

function normalizeSpreadSortValue(value) {

    if (value === null || value === undefined || value === "") {
        return "";
    }

    let normalizedValue = String(value).trim();

    // تبدیل ارقام فارسی به انگلیسی
    normalizedValue = normalizedValue.replace(
        /[۰-۹]/g,
        digit => "۰۱۲۳۴۵۶۷۸۹".indexOf(digit)
    );

    // تبدیل ارقام عربی به انگلیسی
    normalizedValue = normalizedValue.replace(
        /[٠-٩]/g,
        digit => "٠١٢٣٤٥٦٧٨٩".indexOf(digit)
    );

    // حذف کاما از اعداد
    normalizedValue = normalizedValue.replace(/,/g, "");

    // تشخیص تاریخ مانند 1405/05/20
    if (/^\d{4}\/\d{2}\/\d{2}$/.test(normalizedValue)) {

        return Number(
            normalizedValue.replace(/\//g, "")
        );
    }

    // تشخیص عدد
    if (
        normalizedValue !== "" &&
        !Number.isNaN(Number(normalizedValue))
    ) {
        return Number(normalizedValue);
    }

    // مقدار متنی
    return normalizedValue;
}

function getSingleDropdownValue(dropdownId) {
    return document.getElementById(dropdownId)?.dataset.value || "";
}

function setSingleDropdownValue(dropdownId, value) {
    const dropdown = document.getElementById(dropdownId);
    const option = dropdown?.querySelector(
        `.check-dropdown-option[data-value="${value}"]`
    );

    if (option) {
        option.click();
    }
}

function initializeDataSourceDropdown(dropdown) {
    if (!dropdown) {
        return;
    }

    const label = dropdown.querySelector(".check-dropdown-label");
    const options = dropdown.querySelectorAll(".check-dropdown-option");

    options.forEach(option => {
        const selectOption = function () {
            dropdown.dataset.value = option.dataset.value || "";
            options.forEach(item => item.classList.remove("selected"));
            option.classList.add("selected");

            if (label) {
                label.textContent = option.textContent.trim();
            }

            dropdown.classList.toggle(
                "has-selection",
                dropdown.dataset.value !== (dropdown.dataset.defaultValue || "")
            );
            dropdown.classList.remove("open");
            dropdown.querySelector(".check-dropdown-toggle")
                ?.setAttribute("aria-expanded", "false");
        };

        option.addEventListener("click", selectOption);
        option.addEventListener("keydown", event => {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                selectOption();
            }
        });
    });

    initializeCheckDropdown(dropdown);
}

function sortRowsByState(
    data,
    sortState,
    emptyValuesLast = false
) {

    const sortedRows =
        Array.isArray(data)
            ? [...data]
            : [];

    if (
        !sortState?.column ||
        !sortState?.direction
    ) {
        return sortedRows;
    }

    sortedRows.sort((rowA, rowB) => {

        const valueA =
            normalizeSpreadSortValue(
                rowA[sortState.column]
            );

        const valueB =
            normalizeSpreadSortValue(
                rowB[sortState.column]
            );

        if (emptyValuesLast) {

            const emptyA =
                valueA === "" ||
                valueA === null ||
                valueA === undefined;

            const emptyB =
                valueB === "" ||
                valueB === null ||
                valueB === undefined;

            if (emptyA && emptyB) {
                return 0;
            }

            if (emptyA) {
                return 1;
            }

            if (emptyB) {
                return -1;
            }
        }

        if (valueA < valueB) {
            return sortState.direction === "asc"
                ? -1
                : 1;
        }

        if (valueA > valueB) {
            return sortState.direction === "asc"
                ? 1
                : -1;
        }

        return 0;
    });

    return sortedRows;
}

async function loadSpreadData(
    preserveOldData = false
) {

    const baseSymbols =
        getSelectedValues(
            "spread-base-symbol"
        );


    const tradeValue =
        document
            .getElementById(
                "spread-value"
            )
            ?.value
            ?.trim() || "";


    const dataSourceSelect =
        document.getElementById("spread-data-source");


    if (!dataSourceSelect) {

        throw new Error(
            "انتخاب‌گر منبع اطلاعات تب اسپرد پیدا نشد."
        );
    }


    const dataSourceMode = dataSourceSelect.dataset.value || "live";


    const days =
        document
            .getElementById(
                "spread-days"
            )
            ?.value
            ?.trim() || "";


    const applyButton =
        document.getElementById(
            "apply-spread-filter"
        );


    /*
        نماد پایه انتخاب نشده
    */
    if (baseSymbols.length === 0) {

        /*
            در Auto Refresh پیام نده.
            فقط درخواست را لغو کن.
        */
        if (!preserveOldData) {

            alert(
                "لطفاً حداقل یک نماد پایه را انتخاب کنید."
            );
        }

        return false;
    }


    /*
        روز وارد شده ولی نوع فیلتر مشخص نیست
    */
    if (
        days &&
        !spreadDaysFilterType
    ) {

        if (!preserveOldData) {

            alert(
                "برای تعداد روز تا سررسید، یکی از حالت‌های بالا، پایین یا مساوی را انتخاب کنید."
            );
        }

        return false;
    }


    try {

        /*
            فقط ظاهر دکمه تغییر کند.
            هیچ جدولی پاک نمی‌شود.
        */
        if (applyButton) {

            applyButton.disabled =
                true;

            applyButton.textContent =
                "در حال دریافت...";
        }


        /*
            =================================================
            مهم:
            اینجا دیگر نه spreadOriginalData پاک می‌شود
            نه جدول اسپرد
            نه جدول محاسبات
            =================================================
        */


        const requests =
            baseSymbols.map(
                async baseSymbol => {

                    const parameters =
                        new URLSearchParams();


                    parameters.set(
                        "base_symbol",
                        baseSymbol
                    );


                    if (tradeValue) {

                        parameters.set(
                            "value",
                            tradeValue
                        );
                    }


                    parameters.set(
                        "data_source",
                        dataSourceMode
                    );


                    if (days) {

                        parameters.set(
                            "days",
                            days
                        );

                        parameters.set(
                            "days_operator",
                            spreadDaysFilterType
                        );
                    }


                    parameters.set(
                        "_ts",
                        Date.now().toString()
                    );


                    const response =
                        await fetch(
                            `/spread-data?${parameters.toString()}`,
                            {
                                cache: "no-store"
                            }
                        );


                    const result =
                        await response.json();


                    if (!response.ok) {

                        throw new Error(
                            result.error ||
                            `خطا در دریافت اطلاعات ${baseSymbol}`
                        );
                    }


                    if (!Array.isArray(result)) {

                        throw new Error(
                            `خروجی نماد ${baseSymbol} نامعتبر است.`
                        );
                    }


                    return result;
                }
            );


        /*
            تا اینجا جدول قدیمی هنوز روی صفحه است.

            منتظر می‌مانیم تمام درخواست‌ها
            به طور کامل برسند.
        */
        const results =
            await Promise.all(
                requests
            );

        const firstReturnedRow =
            results
                .flat()
                .find(row => row);

        /*
            ساخت داده جدید در حافظه
        */
        const mergedResults =
            results.flat();


        /*
            حذف نمادهای تکراری
        */
        const uniqueMap =
            new Map();


        mergedResults.forEach(row => {

            const optionSymbol =
                row["نماد اختیار"];

            if (!optionSymbol) {
                return;
            }

            uniqueMap.set(
                optionSymbol,
                row
            );
        });


        const newSpreadData =
            Array.from(
                uniqueMap.values()
            );


        /*
            =================================================
            SWAP

            فقط حالا که دیتای جدید کامل رسیده،
            دیتای قبلی را یک‌باره جایگزین می‌کنیم.
            =================================================
        */

        spreadOriginalData =
            newSpreadData;


        /*
            جدول جدید یک‌باره جایگزین جدول قبلی
        */
        renderSpreadTable(
            spreadOriginalData
        );


        /*
            در حالت فیلتر دستی:
            محاسبات قبلی بعد از رسیدن دیتای جدید
            پاک می‌شود.

            در Auto Refresh:
            پاک نمی‌شود، چون چند لحظه بعد
            calculateSpreadTable آن را با
            داده جدید جایگزین می‌کند.
        */
        if (!preserveOldData) {

            resetSpreadCalculationTable();
        }


        return true;


    } catch (error) {

        console.error(
            "Load spread data error:",
            error
        );


        /*
            مهم:
            در خطا هیچ دیتای قبلی پاک نمی‌شود.
        */

        if (!preserveOldData) {

            alert(
                error.message ||
                "خطا در دریافت اطلاعات اسپرد"
            );
        }


        return false;


    } finally {

        if (applyButton) {

            applyButton.disabled =
                false;

            applyButton.textContent =
                "اعمال فیلتر";
        }


    }
}

async function applySpreadFilterAndCalculate() {

    const loadSuccess =
        await loadSpreadData();

    if (
        loadSuccess &&
        Array.isArray(spreadOriginalData) &&
        spreadOriginalData.length >= 2
    ) {

        calculateSpreadTable();
    }
}

document.querySelectorAll(".tab-btn").forEach(btn => {

    btn.addEventListener("click", function () {

        // حذف active از همه دکمه‌ها
        document.querySelectorAll(".tab-btn").forEach(b => 
            b.classList.remove("active")
        );

        // حذف active از همه تب‌ها
        document.querySelectorAll(".tab-content").forEach(tab => 
            tab.classList.remove("active")
        );

        // فعال کردن دکمه کلیک شده
        this.classList.add("active");

        // پیدا کردن تب مربوطه
        const tabId = this.dataset.tab;
        document.getElementById(tabId).classList.add("active");

        if (tabId === "expectations" && !marketExpectationsData) {
            loadMarketExpectations();
        }
    });

});

/* document.querySelectorAll('.arrow-buttons').forEach(group => {

    const buttons = group.querySelectorAll('button');

    buttons.forEach(btn => {
        btn.addEventListener('click', function () {

            // فقط همین گروه
            buttons.forEach(b => b.classList.remove('active'));

            this.classList.add('active');

            // تشخیص اینکه مربوط به کدوم فیلتره
            if (this.id.includes("value")) {
                valueFilterType = this.id.includes("up") ? "gt" : "lt";
            }

            if (this.id.includes("days")) {
                daysFilterType = this.id.includes("up") ? "gt" : "lt";
            }

            if (this.dataset.type) {
                daysFilterType = this.dataset.type;
            }

        
        });
    });

});
*/


function parseSpreadNumber(value) {

    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {
        return null;
    }

    let normalizedValue = String(value).trim();

    // تبدیل اعداد فارسی به انگلیسی
    normalizedValue = normalizedValue.replace(
        /[۰-۹]/g,
        digit => "۰۱۲۳۴۵۶۷۸۹".indexOf(digit)
    );

    // تبدیل اعداد عربی به انگلیسی
    normalizedValue = normalizedValue.replace(
        /[٠-٩]/g,
        digit => "٠١٢٣٤٥٦٧٨٩".indexOf(digit)
    );

    // حذف جداکننده هزارگان و درصد
    normalizedValue = normalizedValue
        .replace(/,/g, "")
        .replace(/٪|%/g, "")
        .trim();

    const numericValue = Number(normalizedValue);

    return Number.isFinite(numericValue)
        ? numericValue
        : null;
}

function roundSpreadNumber(value, digits = 2) {

    if (!Number.isFinite(value)) {
        return null;
    }

    const multiplier = 10 ** digits;

    return Math.round(
        (value + Number.EPSILON) * multiplier
    ) / multiplier;
}

function formatSpreadNumber(value, digits = 2) {

    if (!Number.isFinite(value)) {
        return "";
    }

    return value.toLocaleString("en-US", {
        minimumFractionDigits: 0,
        maximumFractionDigits: digits
    });
}

function calculateSpreadMetrics({
    buyStrike,
    sellStrike,

    buyOptionSellPrice,
    sellOptionBuyPrice,

    buyOptionSellVolume,
    sellOptionBuyVolume,

    baseLastPrice,
    daysRemaining
}) {

    /*
        حداکثر زیان:
        قیمت خرید نماد فروش
        منهای قیمت فروش نماد خرید
    */
    const maxLoss =
        sellOptionBuyPrice - buyOptionSellPrice;

    /*
        هزینه استراتژی
    */
    const strategyCost =
        buyOptionSellPrice - sellOptionBuyPrice;

    /*
        اهرم استراتژی
    */
    const strategyLeverage =
        strategyCost !== 0
            ? baseLastPrice / strategyCost
            : null;

    /*
        حداکثر سود
    */
    const maxProfit =
        (
            sellStrike - buyStrike
        ) + maxLoss;

    /*
        نسبت بازدهی به‌صورت اعشاری

        مثال:
        0.25 یعنی 25 درصد
    */
    const returnRate =
        maxLoss !== 0
            ? maxProfit / Math.abs(maxLoss)
            : null;

    /*
        بازدهی درصدی

        گردکردن در زمان نمایش انجام می‌شود.
    */
    const returnPercent =
        returnRate !== null
            ? returnRate * 100
            : null;

    /*
        ریوارد به ریسک قبلی
    */
    const riskToReward =
        maxLoss !== 0
            ? Math.abs(
                maxProfit / maxLoss
            )
            : null;

    /*
        قیمت سر به سر
    */
    const breakEvenPrice =
        buyStrike - maxLoss;

    /*
        فاصله تا سر به سر به‌صورت درصد

        Math.round حذف شده تا امکان نمایش
        یک رقم اعشار وجود داشته باشد.
    */
    const distanceToBreakEven =
        baseLastPrice !== 0
            ? (
                (
                    breakEvenPrice /
                    baseLastPrice
                ) - 1
            ) * 100
            : null;

    const distanceToMaxLoss =
        baseLastPrice !== 0
            ? (
                (
                    buyStrike /
                    baseLastPrice
                ) - 1
            ) * 100
            : null;

    /*
        فاصله تا حداکثر سود به‌صورت درصد

        قیمت اعمال نماد فروش تقسیم بر
        قیمت فعلی دارایی پایه، منهای یک
    */
    const distanceToMaxProfit =
        baseLastPrice !== 0
            ? (
                (
                    sellStrike / baseLastPrice
                ) - 1
            )  * 100
            : null;

    /*
        حجم قابل معامله
    */
    const tradeableVolume =
        buyOptionSellVolume !== null &&
        sellOptionBuyVolume !== null
            ? Math.min(
                buyOptionSellVolume,
                sellOptionBuyVolume
            )
            : null;

    /*
        مبلغ
    */
    const amount =
        tradeableVolume !== null &&
        buyOptionSellPrice !== null
            ? (
                tradeableVolume *
                buyOptionSellPrice *
                1000
            )
            : null;

    /*
        YTM مطابق فرمول درخواستی:

        (1 + بازدهی اعشاری)
        به توان
        (365 / روز تا سررسید)
        ضرب در 100

        برای جلوگیری از خروجی NaN:
        - روز سررسید باید بیشتر از صفر باشد.
        - پایه توان باید مثبت باشد.
    */
    const ytmBase =
        returnRate !== null
            ? 1 + returnRate
            : null;

    const ytm =
        ytmBase !== null &&
        ytmBase > 0 &&
        daysRemaining !== null &&
        daysRemaining > 0
            ? (Math.pow(
                ytmBase,
                30 / daysRemaining
            ) - 1 ) * 100
            : null;

    return {
        maxLoss,
        maxProfit,

        riskToReward,

        returnRate,
        returnPercent,
        ytm,

        breakEvenPrice,
        distanceToBreakEven,
        distanceToMaxLoss,
        distanceToMaxProfit,

        tradeableVolume,
        amount,
        strategyLeverage
    };
}
function calculateSpreadTable() {

    if (
        !Array.isArray(spreadOriginalData) ||
        spreadOriginalData.length < 2
    ) {
        alert(
            "برای محاسبه اسپرد حداقل دو نماد باید از فیلتر عبور کنند."
        );

        return;
    }

    /*
        گروه‌بندی نمادها بر اساس تاریخ سررسید
    */
    /*
        گروه‌بندی بر اساس دو شرط:

        1. تاریخ سررسید یکسان
        2. نماد پایه یکسان

        بنابراین قراردادهای مربوط به دو دارایی پایه مختلف
        هیچ‌وقت در یک اسپرد قرار نمی‌گیرند.
    */
    const expiryGroups = new Map();

    spreadOriginalData.forEach(row => {

        const expiryDate = String(
            row["تاریخ سررسید"] ?? ""
        ).trim();

        const baseSymbol = String(
            row["نماد پایه"] ?? ""
        ).trim();

        const strikePrice = parseSpreadNumber(
            row["قیمت اعمال"]
        );

        /*
            ردیف‌هایی که اطلاعات ضروری ندارند
            وارد محاسبات نمی‌شوند.
        */
        if (
            !expiryDate ||
            !baseSymbol ||
            strikePrice === null
        ) {
            return;
        }

        /*
            کلید هر گروه از ترکیب نماد پایه
            و تاریخ سررسید ساخته می‌شود.
        */
        const groupKey =
            `${baseSymbol}|||${expiryDate}`;

        if (!expiryGroups.has(groupKey)) {

            expiryGroups.set(groupKey, {
                baseSymbol,
                expiryDate,
                rows: []
            });
        }

        expiryGroups
            .get(groupKey)
            .rows
            .push(row);
    });

    const calculatedRows = [];

    /*
        مرتب‌سازی خود گروه‌های سررسید بر اساس تاریخ
    */
    const sortedExpiryGroups = [
        ...expiryGroups.values()
    ].sort((groupA, groupB) => {

        /*
            ابتدا نمادهای پایه کنار یکدیگر قرار می‌گیرند.
        */
        const baseComparison =
            groupA.baseSymbol.localeCompare(
                groupB.baseSymbol,
                "fa"
            );

        if (baseComparison !== 0) {
            return baseComparison;
        }

        /*
            داخل هر نماد پایه، سررسیدها
            از نزدیک‌ترین به دورترین مرتب می‌شوند.
        */
        const dateA = Number(
            groupA.expiryDate.replace(/\//g, "")
        );

        const dateB = Number(
            groupB.expiryDate.replace(/\//g, "")
        );

        return dateA - dateB;
    });

    sortedExpiryGroups.forEach(group => {

        const {
            baseSymbol,
            expiryDate,
            rows: groupRows
        } = group;

        /*
            حداقل دو قرارداد از یک نماد پایه
            و یک سررسید برای تشکیل اسپرد لازم است.
        */
        if (groupRows.length < 2) {
            return;
        }

        const daysRemaining = parseSpreadNumber(
            groupRows[0]["روز باقی‌مانده"]
        );

            /*
                مرتب‌سازی قیمت اعمال به‌صورت نزولی:
                بالاترین قیمت اعمال در ابتدای آرایه
                و پایین‌ترین در انتهای آرایه.
            */
            const sortedByStrikeDescending = [
                ...groupRows
            ].sort((rowA, rowB) => {

                const strikeA = parseSpreadNumber(
                    rowA["قیمت اعمال"]
                );

                const strikeB = parseSpreadNumber(
                    rowB["قیمت اعمال"]
                );

                return strikeB - strikeA;
            });

            /*
                چون نماد خرید باید کمترین قیمت اعمال
                را داشته باشد، پیمایش خرید از انتهای
                آرایه نزولی شروع می‌شود.
            */
            for (
                let buyIndex =
                    sortedByStrikeDescending.length - 1;

                buyIndex >= 1;

                buyIndex--
            ) {

                const buyRow =
                    sortedByStrikeDescending[buyIndex];

                const buyOrderBook =
                    Array.isArray(
                        buyRow["__orderBook"]
                    )
                        ? buyRow["__orderBook"]
                        : [];

                const buySymbol =
                    buyRow["نماد اختیار"];

                const buyInsCode =
                    buyRow["__insCode"];

                const buyBaseSymbol = String(
                    buyRow["نماد پایه"] ?? ""
                ).trim();

                const buyStrike = parseSpreadNumber(
                    buyRow["قیمت اعمال"]
                );

                /*
                 چون این نماد در ستون خرید قرار دارد،
                 برای خرید آن باید از قیمت فروش بازار استفاده کنیم.
                */
                const buyOptionSellPrice = parseSpreadNumber(
                    buyRow["قیمت فروش"]
                );

                /*
                    حجم قابل خرید از این نماد،
                    همان حجم فروش موجود در سرخط فروش است.
                */
                const buyOptionSellVolume = parseSpreadNumber(
                    buyRow["حجم فروش"]
                );

                const baseLastPrice = parseSpreadNumber(
                    buyRow["آخرین قیمت نماد پایه"]
                );

                if (
                    buyStrike === null ||
                    buyOptionSellPrice === null ||
                    baseLastPrice === null
                ) {
                    continue;
                }

                /*
                    نمادهای قبل از buyIndex همگی
                    قیمت اعمال بالاتری دارند.
                */
                for (
                    let sellIndex = 0;

                    sellIndex < buyIndex;

                    sellIndex++
                ) {

                    const sellRow =
                        sortedByStrikeDescending[
                            sellIndex
                        ];

                    const sellOrderBook =
                        Array.isArray(
                            sellRow["__orderBook"]
                        )
                            ? sellRow["__orderBook"]
                            : [];

                    const sellSymbol =
                        sellRow["نماد اختیار"];

                    const sellInsCode =
                        sellRow["__insCode"];

                    const sellBaseSymbol = String(
                        sellRow["نماد پایه"] ?? ""
                    ).trim();

                    const sellStrike =
                        parseSpreadNumber(
                            sellRow["قیمت اعمال"]
                        );

                    /*
                        چون این نماد در ستون فروش قرار دارد،
                        برای فروش آن باید از قیمت خرید بازار استفاده کنیم.
                    */
                    const sellOptionBuyPrice =
                        parseSpreadNumber(
                            sellRow["قیمت خرید"]
                        );

                    /*
                        حجم قابل فروش از این نماد،
                        همان حجم خرید موجود در سرخط خرید است.
                    */
                    const sellOptionBuyVolume =
                        parseSpreadNumber(
                            sellRow["حجم خرید"]
                        );

                    if (
                        sellStrike === null ||
                        sellOptionBuyPrice === null
                    ) {
                        continue;
                    }

                    /*
                        فقط قیمت اعمال بالاتر به‌عنوان
                        نماد فروش پذیرفته می‌شود.
                        این شرط نمادهای دارای قیمت
                        اعمال مساوی را حذف می‌کند.
                    */
                    if (sellStrike <= buyStrike) {
                        continue;
                    }
                    /*
                        جلوگیری قطعی از ترکیب قراردادهای
                        مربوط به دو دارایی پایه متفاوت
                    */
                    if (
                        !buyBaseSymbol ||
                        !sellBaseSymbol ||
                        buyBaseSymbol !== sellBaseSymbol
                    ) {
                        continue;
                    }
                    const metrics =
                        calculateSpreadMetrics({
                            buyStrike,
                            sellStrike,

                            buyOptionSellPrice,
                            sellOptionBuyPrice,

                            buyOptionSellVolume,
                            sellOptionBuyVolume,

                            baseLastPrice,
                            daysRemaining
                        });

                    const buyTradeValue =
                        parseSpreadNumber(
                            buyRow["ارزش معاملات"]
                        );

                    const sellTradeValue =
                        parseSpreadNumber(
                            sellRow["ارزش معاملات"]
                        );

                    /*
                        حذف ترکیب دارای حداکثر سود منفی
                    */
                    if (
                        metrics.maxProfit === null ||
                        !Number.isFinite(metrics.maxProfit) ||
                        metrics.maxProfit < 0
                    ) {
                        continue;
                    }
                    calculatedRows.push({              

                                                    /*
                                اطلاعات فنی برای Order Book
                                در جدول نمایش داده نمی‌شوند.
                            */
                        "__buyOrderBook":
                            buyOrderBook,

                        "__sellOrderBook":
                            sellOrderBook,

                        "__payoff": {

                            buyStrike,
                            sellStrike,

                            buyPremium:
                                buyOptionSellPrice,

                            sellPremium:
                                sellOptionBuyPrice,

                            baseLastPrice,

                            daysRemaining,

                            maxLoss:
                                metrics.maxLoss,

                            maxProfit:
                                metrics.maxProfit,

                            breakEvenPrice:
                                metrics.breakEvenPrice,

                            distanceToMaxLoss:
                                metrics.distanceToMaxLoss,

                            distanceToBreakEven:
                                metrics.distanceToBreakEven,

                            distanceToMaxProfit:
                                metrics.distanceToMaxProfit
                        },

                        "نماد پایه":
                            baseSymbol,

                        /*
                            اضافه‌شدن تاریخ سررسید برای
                            تشخیص دسته‌ها ضروری است.
                        */

                        "خرید":
                            buySymbol,

                        "فروش":
                            sellSymbol,

                        /*
                            قیمت فروش نمادی که در ستون خرید است
                        */
                        "قیمت فروش نماد خرید":
                            formatSpreadNumber(
                                buyOptionSellPrice
                            ),

                        /*
                            قیمت خرید نمادی که در ستون فروش است
                        */
                        "قیمت خرید نماد فروش":
                            formatSpreadNumber(
                                sellOptionBuyPrice
                            ),

                        "اهرم استراتژی":
                            metrics.strategyLeverage !== null
                                ? formatSpreadNumber(
                                    metrics.strategyLeverage,
                                    2
                                )
                                : "",

                        "حداکثر زیان":
                            formatSpreadNumber(
                                metrics.maxLoss
                            ),

                        "حداکثر سود":
                            formatSpreadNumber(
                                metrics.maxProfit
                            ),

                        // "بازدهی ٪":
                        //     metrics.returnPercent !== null
                        //         ? formatSpreadNumber(
                        //             metrics.returnPercent,
                        //             0
                        //         )
                        //         : "",
                        "روز تا سررسید":
                            daysRemaining !== null
                                ? daysRemaining
                                : "",

                        "YTM ماهانه ٪":
                            metrics.ytm !== null
                                ? formatSpreadNumber(
                                    metrics.ytm,
                                    1
                                )
                                : "",

                        "  ریوارد به ریسک":
                            metrics.riskToReward !== null
                                ? formatSpreadNumber(
                                    metrics.riskToReward,
                                    2
                                )
                                : "",

                        // "قیمت سر به سر":
                        //     formatSpreadNumber(
                        //         metrics.breakEvenPrice
                        //     ),

                        "فاصله تا سر به سر %":
                            metrics.distanceToBreakEven !== null
                                ? formatSpreadNumber(
                                    metrics.distanceToBreakEven,
                                    1
                                )
                                : "",

                        "فاصله تا حداکثر سود %":
                            metrics.distanceToMaxProfit !== null
                                ? formatSpreadNumber(
                                    metrics.distanceToMaxProfit,
                                    3
                                )
                                : "",

                        "حجم قابل معامله":
                            metrics.tradeableVolume !== null
                                ? formatSpreadNumber(
                                    metrics.tradeableVolume,
                                    0
                                )
                                : "",

                    

                        "مبلغ":
                            metrics.amount !== null
                                ? formatSpreadNumber(
                                    metrics.amount,
                                    0
                                )
                                : "",
                        "__buyReport": {

                            symbol:
                                buySymbol,

                            openInterest:
                                buyRow["موقعیت باز"] ?? "",

                            status:
                                buyRow["وضعیت"] ?? "",

                            lastPrice:
                                buyRow["آخرین قیمت نماد اختیار"] ?? "",

                            closePrice:
                                buyRow["__optionClosePrice"] ?? "",

                            tradeValue:
                                buyTradeValue !== null
                                    ? formatSpreadNumber(
                                        buyTradeValue /
                                        1_000_000,
                                        1
                                    )
                                    : "",

                            tradeVolume:
                                buyRow["__tradeVolume"] ?? ""
                        },


                        "__sellReport": {

                            symbol:
                                sellSymbol,

                            openInterest:
                                sellRow["موقعیت باز"] ?? "",

                            status:
                                sellRow["وضعیت"] ?? "",

                            lastPrice:
                                sellRow["آخرین قیمت نماد اختیار"] ?? "",

                            closePrice:
                                sellRow["__optionClosePrice"] ?? "",

                            tradeValue:
                                sellTradeValue !== null
                                    ? formatSpreadNumber(
                                        sellTradeValue /
                                        1_000_000,
                                        1
                                    )
                                    : "",

                            tradeVolume:
                                sellRow["__tradeVolume"] ?? ""
                        },
                        "__baseReport": {

                            symbol:
                                baseSymbol,

                            lastPrice:
                                buyRow["آخرین قیمت نماد پایه"] ?? "",

                            closePrice:
                                buyRow["__baseClosePrice"] ?? ""
                        },
                    });
                }
            }
        }
    );

    spreadCalculationOriginalData =
        calculatedRows;

    spreadCalculationCurrentData =
        sortRowsByState(
            calculatedRows,
            spreadCalculationSort,
            true
        );


    const calculationSection =
        document.getElementById(
            "spread-calculation-section"
        );


    if (calculatedRows.length === 0) {

        if (calculationSection) {

            calculationSection.style.display =
                "none";
        }

        alert(
            "هیچ ترکیب اسپردی مطابق شرایط موجود پیدا نشد."
        );

        return;
    }


    /*
        حداقل یک اسپرد وجود دارد
    */
    if (calculationSection) {

        calculationSection.style.display =
            "block";
    }


    renderSpreadCalculationTable(
        spreadCalculationCurrentData,
        true
    );
    
}

function renderSpreadColumnControls(headers) {

    const container =
        document.getElementById(
            "spread-column-options"
        );

    if (!container) {
        return;
    }


    container.innerHTML = "";


    headers.forEach(header => {

        const label =
            document.createElement("label");

        label.className =
            "spread-column-option";


        const checkbox =
            document.createElement("input");

        checkbox.type = "checkbox";
        checkbox.value = header;


        checkbox.checked =
            !hiddenSpreadCalculationColumns.has(
                header
            );


        const text =
            document.createElement("span");

        text.textContent = header;


        checkbox.addEventListener(
            "change",
            function () {

                if (this.checked) {

                    hiddenSpreadCalculationColumns.delete(
                        header
                    );

                } else {

                    hiddenSpreadCalculationColumns.add(
                        header
                    );
                }


                renderSpreadCalculationTable(
                    spreadCalculationCurrentData,
                    false
                );
            }
        );


        label.appendChild(
            checkbox
        );

        label.appendChild(
            text
        );

        container.appendChild(
            label
        );
    });
}

function showAllSpreadColumns() {

    /*
        هیچ ستونی مخفی نباشد
    */
    hiddenSpreadCalculationColumns.clear();


    /*
        تمام checkboxهای موجود نیز
        مستقیماً تیک بخورند
    */
    document
        .querySelectorAll(
            '#spread-column-options input[type="checkbox"]'
        )
        .forEach(checkbox => {

            checkbox.checked = true;

        });


    /*
        جدول دوباره ساخته شود
        بدون اینکه کنترل‌ها از نو ساخته شوند
    */
    renderSpreadCalculationTable(
        spreadCalculationCurrentData,
        false
    );
}

function hideAllSpreadColumns() {

    if (
        !Array.isArray(spreadCalculationCurrentData) ||
        spreadCalculationCurrentData.length === 0
    ) {
        return;
    }


    const headers = Object.keys(
        spreadCalculationCurrentData[0]
    );


    /*
        همه ستون‌ها وارد لیست مخفی شوند
    */
    headers.forEach(header => {

        hiddenSpreadCalculationColumns.add(
            header
        );

    });


    /*
        برداشتن تمام تیک‌ها
    */
    document
        .querySelectorAll(
            '#spread-column-options input[type="checkbox"]'
        )
        .forEach(checkbox => {

            checkbox.checked = false;

        });


    renderSpreadCalculationTable(
        spreadCalculationCurrentData,
        false
    );
}

function renderOrderBookTable(
    tableId,
    rows
) {

    const tbody =
        document.querySelector(
            `#${tableId} tbody`
        );

    if (!tbody) {

        console.error(
            "OrderBook table not found:",
            tableId
        );

        return;
    }


    tbody.innerHTML = "";


    /*
        جدول همیشه 5 ردیف دارد
    */
    for (
        let index = 0;
        index < 5;
        index++
    ) {

        const row =
            Array.isArray(rows)
                ? rows[index]
                : null;


        const tr =
            document.createElement("tr");


        const values = row
            ? [
                row["ردیف"],
                row["تعداد سفارش خرید"],
                row["حجم خرید"],
                row["قیمت خرید"],
                row["قیمت فروش"],
                row["حجم فروش"],
                row["تعداد سفارش فروش"]
            ]
            : [
                index + 1,
                "",
                "",
                "",
                "",
                "",
                ""
            ];


        values.forEach(
            (value, cellIndex) => {

                const td =
                    document.createElement(
                        "td"
                    );


                let displayedValue =
                    value ?? "";


                /*
                    فرمت عدد به جز شماره ردیف
                */
                if (
                    cellIndex > 0 &&
                    displayedValue !== "" &&
                    Number.isFinite(
                        Number(displayedValue)
                    )
                ) {

                    displayedValue =
                        Number(
                            displayedValue
                        ).toLocaleString(
                            "en-US"
                        );
                }


                td.textContent =
                    displayedValue;


                tr.appendChild(
                    td
                );
            }
        );


        tbody.appendChild(
            tr
        );
    }
}

function setSpreadReportValue(
    elementId,
    value
) {

    const element =
        document.getElementById(
            elementId
        );


    if (!element) {
        return;
    }


    const hasValue =
        value !== null &&
        value !== undefined &&
        String(value).trim() !== "";


    element.textContent =
        hasValue
            ? value
            : "-";
}

const SPREAD_PAYOFF_SVG_NAMESPACE =
    "http://www.w3.org/2000/svg";

function createSpreadPayoffSvgElement(
    tagName,
    attributes = {},
    text = ""
) {

    const element =
        document.createElementNS(
            SPREAD_PAYOFF_SVG_NAMESPACE,
            tagName
        );

    Object.entries(attributes).forEach(
        ([name, value]) => {

            element.setAttribute(
                name,
                String(value)
            );
        }
    );

    if (text !== "") {
        element.textContent = text;
    }

    return element;
}

function getSpreadPayoffAtPrice(
    basePrice,
    payoff
) {

    if (basePrice <= payoff.buyStrike) {
        return payoff.maxLoss;
    }

    if (basePrice < payoff.sellStrike) {

        return (
            basePrice +
            payoff.maxLoss -
            payoff.buyStrike
        );
    }

    return payoff.maxProfit;
}

function getSpreadPayoffTicks(
    minimum,
    maximum,
    targetCount = 6
) {

    const range = maximum - minimum;

    if (
        !Number.isFinite(range) ||
        range <= 0
    ) {
        return [minimum];
    }

    const roughStep =
        range / Math.max(targetCount - 1, 1);

    const magnitude =
        10 ** Math.floor(
            Math.log10(roughStep)
        );

    const normalizedStep =
        roughStep / magnitude;

    let niceMultiplier = 10;

    if (normalizedStep <= 1) {
        niceMultiplier = 1;
    } else if (normalizedStep <= 2) {
        niceMultiplier = 2;
    } else if (normalizedStep <= 2.5) {
        niceMultiplier = 2.5;
    } else if (normalizedStep <= 5) {
        niceMultiplier = 5;
    }

    const step =
        niceMultiplier * magnitude;

    const firstTick =
        Math.ceil(minimum / step) * step;

    const ticks = [];

    for (
        let tick = firstTick;
        tick <= maximum + step * 0.001;
        tick += step
    ) {

        ticks.push(
            Math.abs(tick) < step * 0.001
                ? 0
                : tick
        );
    }

    return ticks;
}

function formatSpreadPayoffPercent(value) {

    if (!Number.isFinite(value)) {
        return "-";
    }

    const sign = value > 0
        ? "+"
        : "";

    return `${sign}${formatSpreadNumber(value, 1)}٪`;
}

function isolateSpreadPayoffText(value) {

    return `\u2066${value}\u2069`;
}

function renderSpreadPayoffChart(row) {

    const svg =
        document.getElementById(
            "spread-payoff-svg"
        );

    const emptyState =
        document.getElementById(
            "spread-payoff-empty"
        );

    const summary =
        document.getElementById(
            "spread-payoff-summary"
        );

    const chart =
        svg?.closest(
            ".spread-payoff-chart"
        );

    const tooltip =
        document.getElementById(
            "spread-payoff-tooltip"
        );

    const tooltipPrice =
        document.getElementById(
            "spread-payoff-tooltip-price"
        );

    const tooltipPricePercent =
        document.getElementById(
            "spread-payoff-tooltip-price-percent"
        );

    const tooltipValue =
        document.getElementById(
            "spread-payoff-tooltip-value"
        );

    const tooltipValuePercent =
        document.getElementById(
            "spread-payoff-tooltip-value-percent"
        );

    const tooltipMonthly =
        document.getElementById(
            "spread-payoff-tooltip-monthly"
        );

    if (
        !svg ||
        !emptyState ||
        !summary ||
        !chart ||
        !tooltip ||
        !tooltipPrice ||
        !tooltipPricePercent ||
        !tooltipValue ||
        !tooltipValuePercent ||
        !tooltipMonthly
    ) {
        return;
    }

    const source =
        row?.["__payoff"] &&
        typeof row["__payoff"] === "object"
            ? row["__payoff"]
            : {};

    const payoff = {
        buyStrike:
            parseSpreadNumber(source.buyStrike),

        sellStrike:
            parseSpreadNumber(source.sellStrike),

        buyPremium:
            parseSpreadNumber(source.buyPremium),

        sellPremium:
            parseSpreadNumber(source.sellPremium),

        baseLastPrice:
            parseSpreadNumber(source.baseLastPrice),

        daysRemaining:
            parseSpreadNumber(source.daysRemaining),

        maxLoss:
            parseSpreadNumber(source.maxLoss),

        maxProfit:
            parseSpreadNumber(source.maxProfit),

        breakEvenPrice:
            parseSpreadNumber(source.breakEvenPrice),

        distanceToMaxLoss:
            parseSpreadNumber(source.distanceToMaxLoss),

        distanceToBreakEven:
            parseSpreadNumber(source.distanceToBreakEven),

        distanceToMaxProfit:
            parseSpreadNumber(source.distanceToMaxProfit)
    };

    const requiredValues = [
        payoff.buyStrike,
        payoff.sellStrike,
        payoff.baseLastPrice,
        payoff.maxLoss,
        payoff.maxProfit,
        payoff.breakEvenPrice
    ];

    const isValid =
        requiredValues.every(
            value => Number.isFinite(value)
        ) &&
        payoff.sellStrike > payoff.buyStrike;

    svg.replaceChildren();
    tooltip.hidden = true;
    svg.onpointermove = null;
    svg.onpointerleave = null;

    if (!isValid) {

        svg.hidden = true;
        emptyState.hidden = false;
        summary.textContent = "-";

        return;
    }

    svg.hidden = false;
    emptyState.hidden = true;

    const buySymbol =
        String(row?.["خرید"] ?? "").trim();

    const sellSymbol =
        String(row?.["فروش"] ?? "").trim();

    const currentPayoff =
        getSpreadPayoffAtPrice(
            payoff.baseLastPrice,
            payoff
        );

    summary.textContent = [
        `سر‌به‌سر: ${isolateSpreadPayoffText(formatSpreadNumber(payoff.breakEvenPrice, 0))}`,
        `حداکثر زیان: ${isolateSpreadPayoffText(formatSpreadNumber(payoff.maxLoss, 0))}`,
        `حداکثر سود: ${isolateSpreadPayoffText(formatSpreadNumber(payoff.maxProfit, 0))}`,
        `روز تا سررسید: ${isolateSpreadPayoffText(formatSpreadNumber(payoff.daysRemaining, 0))}`
    ].join("  |  ");

    const width = 920;
    const height = 440;

    const margin = {
        top: 84,
        right: 34,
        bottom: 70,
        left: 104
    };

    const plotWidth =
        width - margin.left - margin.right;

    const plotHeight =
        height - margin.top - margin.bottom;

    const strikeDistance =
        payoff.sellStrike - payoff.buyStrike;

    const horizontalPadding = Math.max(
        strikeDistance * 0.6,
        payoff.baseLastPrice * 0.06,
        1
    );

    const xMinimum = Math.max(
        0,
        Math.min(
            payoff.buyStrike,
            payoff.baseLastPrice
        ) - horizontalPadding
    );

    const xMaximum =
        Math.max(
            payoff.sellStrike,
            payoff.baseLastPrice
        ) + horizontalPadding;

    const payoffPrices = [
        xMinimum,
        payoff.buyStrike,
        payoff.sellStrike,
        xMaximum
    ].filter(
        (value, index, values) =>
            index === 0 ||
            value !== values[index - 1]
    );

    const payoffValues =
        payoffPrices.map(
            price =>
                getSpreadPayoffAtPrice(
                    price,
                    payoff
                )
        );

    const rawYMinimum = Math.min(
        0,
        currentPayoff,
        ...payoffValues
    );

    const rawYMaximum = Math.max(
        0,
        currentPayoff,
        ...payoffValues
    );

    const yRange = Math.max(
        rawYMaximum - rawYMinimum,
        Math.abs(rawYMinimum) * 0.25,
        Math.abs(rawYMaximum) * 0.25,
        1
    );

    const yMinimum =
        rawYMinimum - yRange * 0.16;

    const yMaximum =
        rawYMaximum + yRange * 0.16;

    const xScale = value =>
        margin.left +
        (
            (value - xMinimum) /
            (xMaximum - xMinimum)
        ) * plotWidth;

    const yScale = value =>
        margin.top +
        (
            (yMaximum - value) /
            (yMaximum - yMinimum)
        ) * plotHeight;

    const title =
        createSpreadPayoffSvgElement(
            "title",
            { id: "spread-payoff-svg-title" },
            `نمودار سود و زیان ${buySymbol} و ${sellSymbol}`
        );

    const description =
        createSpreadPayoffSvgElement(
            "desc",
            { id: "spread-payoff-svg-description" },
            `محور افقی آخرین قیمت نماد پایه و محور عمودی سود یا زیان در سررسید است. آخرین قیمت فعلی ${formatSpreadNumber(payoff.baseLastPrice, 0)} است.`
        );

    svg.append(title, description);

    const zeroY = yScale(0);

    const definitions =
        createSpreadPayoffSvgElement(
            "defs"
        );

    const profitClip =
        createSpreadPayoffSvgElement(
            "clipPath",
            { id: "spread-payoff-profit-clip" }
        );

    profitClip.appendChild(
        createSpreadPayoffSvgElement(
            "rect",
            {
                x: margin.left,
                y: margin.top,
                width: plotWidth,
                height: Math.max(
                    zeroY - margin.top,
                    0
                )
            }
        )
    );

    const lossClip =
        createSpreadPayoffSvgElement(
            "clipPath",
            { id: "spread-payoff-loss-clip" }
        );

    lossClip.appendChild(
        createSpreadPayoffSvgElement(
            "rect",
            {
                x: margin.left,
                y: zeroY,
                width: plotWidth,
                height: Math.max(
                    margin.top + plotHeight - zeroY,
                    0
                )
            }
        )
    );

    definitions.append(
        profitClip,
        lossClip
    );

    svg.appendChild(definitions);

    const xTicks =
        getSpreadPayoffTicks(
            xMinimum,
            xMaximum,
            7
        );

    const yTicks =
        getSpreadPayoffTicks(
            yMinimum,
            yMaximum,
            6
        );

    yTicks.forEach(tick => {

        const y = yScale(tick);

        svg.appendChild(
            createSpreadPayoffSvgElement(
                "line",
                {
                    x1: margin.left,
                    y1: y,
                    x2: margin.left + plotWidth,
                    y2: y,
                    class:
                        tick === 0
                            ? "spread-payoff-zero-line"
                            : "spread-payoff-grid-line"
                }
            )
        );

        svg.appendChild(
            createSpreadPayoffSvgElement(
                "text",
                {
                    x: margin.left - 13,
                    y: y + 4,
                    class: "spread-payoff-axis-tick",
                    "text-anchor": "end"
                },
                formatSpreadNumber(
                    tick,
                    Math.abs(tick) < 10 ? 1 : 0
                )
            )
        );
    });

    xTicks.forEach(tick => {

        const x = xScale(tick);

        svg.appendChild(
            createSpreadPayoffSvgElement(
                "line",
                {
                    x1: x,
                    y1: margin.top,
                    x2: x,
                    y2: margin.top + plotHeight,
                    class: "spread-payoff-grid-line"
                }
            )
        );

        svg.appendChild(
            createSpreadPayoffSvgElement(
                "text",
                {
                    x,
                    y: margin.top + plotHeight + 24,
                    class: "spread-payoff-axis-tick",
                    "text-anchor": "middle"
                },
                formatSpreadNumber(tick, 0)
            )
        );
    });

    const chartPoints =
        payoffPrices.map(
            (price, index) => ({
                x: xScale(price),
                y: yScale(payoffValues[index])
            })
        );

    const linePoints =
        chartPoints
            .map(point => `${point.x},${point.y}`)
            .join(" ");

    const areaPoints = [
        `${chartPoints[0].x},${zeroY}`,
        ...chartPoints.map(
            point => `${point.x},${point.y}`
        ),
        `${chartPoints[chartPoints.length - 1].x},${zeroY}`
    ].join(" ");

    [
        {
            className: "spread-payoff-profit-area",
            clipPath: "url(#spread-payoff-profit-clip)"
        },
        {
            className: "spread-payoff-loss-area",
            clipPath: "url(#spread-payoff-loss-clip)"
        }
    ].forEach(area => {

        svg.appendChild(
            createSpreadPayoffSvgElement(
                "polygon",
                {
                    points: areaPoints,
                    class: area.className,
                    "clip-path": area.clipPath
                }
            )
        );
    });

    svg.appendChild(
        createSpreadPayoffSvgElement(
            "polyline",
            {
                points: linePoints,
                class: "spread-payoff-line"
            }
        )
    );

    [
        {
            price: payoff.buyStrike,
            className:
                "spread-payoff-strike-point spread-payoff-buy-point"
        },
        {
            price: payoff.sellStrike,
            className:
                "spread-payoff-strike-point spread-payoff-sell-point"
        }
    ].forEach(marker => {

        svg.appendChild(
            createSpreadPayoffSvgElement(
                "circle",
                {
                    cx: xScale(marker.price),
                    cy: yScale(
                        getSpreadPayoffAtPrice(
                            marker.price,
                            payoff
                        )
                    ),
                    r: 6,
                    class: marker.className
                }
            )
        );
    });

    if (
        payoff.breakEvenPrice >= xMinimum &&
        payoff.breakEvenPrice <= xMaximum
    ) {

        const breakEvenX =
            xScale(payoff.breakEvenPrice);

        svg.appendChild(
            createSpreadPayoffSvgElement(
                "circle",
                {
                    cx: breakEvenX,
                    cy: zeroY,
                    r: 5,
                    class: "spread-payoff-break-even-point"
                }
            )
        );

    }

    const currentX =
        xScale(payoff.baseLastPrice);

    const currentY =
        yScale(currentPayoff);

    svg.appendChild(
        createSpreadPayoffSvgElement(
            "circle",
            {
                cx: currentX,
                cy: currentY,
                r: 6,
                class: "spread-payoff-current-point"
            }
        )
    );

    const plotRight =
        margin.left + plotWidth;

    const plotBottom =
        margin.top + plotHeight;

    [
        {
            title: "آخرین قیمت فعلی",
            value:
                isolateSpreadPayoffText(
                    formatSpreadNumber(
                        payoff.baseLastPrice,
                        0
                    )
                ),
            className: "spread-payoff-current-legend-point"
        },
        {
            title: "اعمال فروش",
            value: `${isolateSpreadPayoffText(formatSpreadNumber(payoff.sellStrike, 0))} (${isolateSpreadPayoffText(formatSpreadPayoffPercent(payoff.distanceToMaxProfit))})`,
            className: "spread-payoff-sell-point"
        },
        {
            title: "سر‌به‌سر",
            value: `${isolateSpreadPayoffText(formatSpreadNumber(payoff.breakEvenPrice, 0))} (${isolateSpreadPayoffText(formatSpreadPayoffPercent(payoff.distanceToBreakEven))})`,
            className: "spread-payoff-break-even-legend-point"
        },
        {
            title: "اعمال خرید",
            value: `${isolateSpreadPayoffText(formatSpreadNumber(payoff.buyStrike, 0))} (${isolateSpreadPayoffText(formatSpreadPayoffPercent(payoff.distanceToMaxLoss))})`,
            className: "spread-payoff-buy-point"
        }
    ].forEach((marker, index) => {

        const rowY =
            plotBottom - 74 + index * 20;

        svg.appendChild(
            createSpreadPayoffSvgElement(
                "text",
                {
                    x: plotRight - 30,
                    y: rowY + 4,
                    class: "spread-payoff-corner-title",
                    "text-anchor": "end"
                },
                marker.title
            )
        );

        svg.appendChild(
            createSpreadPayoffSvgElement(
                "text",
                {
                    x: plotRight - 250,
                    y: rowY + 4,
                    class: "spread-payoff-corner-value",
                    "text-anchor": "start"
                },
                marker.value
            )
        );

        svg.appendChild(
            createSpreadPayoffSvgElement(
                "circle",
                {
                    cx: plotRight - 18,
                    cy: rowY,
                    r: 4,
                    class:
                        `spread-payoff-corner-legend-point ${marker.className}`
                }
            )
        );
    });

    svg.appendChild(
        createSpreadPayoffSvgElement(
            "text",
            {
                x: margin.left + plotWidth / 2,
                y: height - 14,
                class: "spread-payoff-axis-title",
                "text-anchor": "middle"
            },
            "آخرین قیمت نماد پایه (ریال)"
        )
    );

    svg.appendChild(
        createSpreadPayoffSvgElement(
            "text",
            {
                x: 25,
                y: margin.top + plotHeight / 2,
                class: "spread-payoff-axis-title",
                "text-anchor": "middle",
                transform:
                    `rotate(-90 25 ${margin.top + plotHeight / 2})`
            },
            "سود / زیان (ریال)"
        )
    );

    const hoverGuide =
        createSpreadPayoffSvgElement(
            "line",
            {
                x1: margin.left,
                y1: margin.top,
                x2: margin.left,
                y2: margin.top + plotHeight,
                class: "spread-payoff-hover-guide",
                visibility: "hidden"
            }
        );

    const hoverPoint =
        createSpreadPayoffSvgElement(
            "circle",
            {
                cx: margin.left,
                cy: zeroY,
                r: 5,
                class: "spread-payoff-hover-point",
                visibility: "hidden"
            }
        );

    svg.append(
        hoverGuide,
        hoverPoint
    );

    svg.onpointermove = event => {

        const svgBounds =
            svg.getBoundingClientRect();

        const pointerSvgX =
            (
                (event.clientX - svgBounds.left) /
                svgBounds.width
            ) * width;

        const hoverX = Math.min(
            margin.left + plotWidth,
            Math.max(
                margin.left,
                pointerSvgX
            )
        );

        const hoveredPrice =
            xMinimum +
            (
                (hoverX - margin.left) /
                plotWidth
            ) * (xMaximum - xMinimum);

        const hoveredPayoff =
            getSpreadPayoffAtPrice(
                hoveredPrice,
                payoff
            );

        const hoveredY =
            yScale(hoveredPayoff);

        const priceChangePercent =
            payoff.baseLastPrice !== 0
                ? (
                    (
                        hoveredPrice /
                        payoff.baseLastPrice
                    ) - 1
                ) * 100
                : null;

        const payoffPercent =
            payoff.maxLoss !== 0
                ? (
                    hoveredPayoff /
                    Math.abs(payoff.maxLoss)
                ) * 100
                : null;

        const monthlyPercent =
            Number.isFinite(payoff.daysRemaining) &&
            payoff.daysRemaining > 0 &&
            payoffPercent !== null
                ? (
                    30 /
                    payoff.daysRemaining
                ) * payoffPercent
                : null;

        hoverGuide.setAttribute(
            "x1",
            hoverX
        );

        hoverGuide.setAttribute(
            "x2",
            hoverX
        );

        hoverGuide.setAttribute(
            "visibility",
            "visible"
        );

        hoverPoint.setAttribute(
            "cx",
            hoverX
        );

        hoverPoint.setAttribute(
            "cy",
            hoveredY
        );

        hoverPoint.setAttribute(
            "visibility",
            "visible"
        );

        tooltipPrice.textContent =
            formatSpreadNumber(
                hoveredPrice,
                0
            );

        tooltipPricePercent.textContent =
            formatSpreadPayoffPercent(
                priceChangePercent
            );

        tooltipValue.textContent =
            formatSpreadNumber(
                hoveredPayoff,
                0
            );

        tooltipValuePercent.textContent =
            formatSpreadPayoffPercent(
                payoffPercent
            );

        tooltipMonthly.textContent =
            formatSpreadPayoffPercent(
                monthlyPercent
            );

        tooltip.hidden = false;

        const chartBounds =
            chart.getBoundingClientRect();

        const desiredLeft =
            event.clientX -
            chartBounds.left +
            chart.scrollLeft +
            14;

        const minimumLeft =
            chart.scrollLeft + 8;

        const maximumLeft =
            chart.scrollLeft +
            chart.clientWidth -
            tooltip.offsetWidth -
            8;

        tooltip.style.left =
            `${Math.max(
                minimumLeft,
                Math.min(
                    desiredLeft,
                    maximumLeft
                )
            )}px`;

        const desiredTop =
            event.clientY -
            chartBounds.top -
            tooltip.offsetHeight -
            12;

        tooltip.style.top =
            `${Math.max(8, desiredTop)}px`;
    };

    svg.onpointerleave = () => {

        tooltip.hidden = true;

        hoverGuide.setAttribute(
            "visibility",
            "hidden"
        );

        hoverPoint.setAttribute(
            "visibility",
            "hidden"
        );
    };
}

function showSpreadOrderBooks(row) {

    const box =
        document.getElementById(
            "spread-orderbook-box"
        );


    if (!box) {

        console.error(
            "spread-orderbook-box پیدا نشد."
        );

        return;
    }


    const buySymbol =
        row["خرید"] ?? "";

    const sellSymbol =
        row["فروش"] ?? "";


    const buyOrderBook =
        Array.isArray(
            row["__buyOrderBook"]
        )
            ? row["__buyOrderBook"]
            : [];


    const sellOrderBook =
        Array.isArray(
            row["__sellOrderBook"]
        )
            ? row["__sellOrderBook"]
            : [];


    /*
        دریافت گزارش‌های ذخیره‌شده
        داخل ردیف محاسبات اسپرد
    */
    const baseReport =
        row["__baseReport"] &&
        typeof row["__baseReport"] === "object"
            ? row["__baseReport"]
            : {};


    const buyReport =
        row["__buyReport"] &&
        typeof row["__buyReport"] === "object"
            ? row["__buyReport"]
            : {};


    const sellReport =
        row["__sellReport"] &&
        typeof row["__sellReport"] === "object"
            ? row["__sellReport"]
            : {};


    /*
        نمایش کادر
    */
    box.style.display =
        "block";


    /*
        عنوان کلی
    */
    setSpreadReportValue(
        "spread-orderbook-description",
        `${buySymbol} / ${sellSymbol}`
    );


    /*
        نام نمادها بالای جدول سفارشات
    */
    setSpreadReportValue(
        "buy-orderbook-symbol",
        buySymbol
    );

    setSpreadReportValue(
        "sell-orderbook-symbol",
        sellSymbol
    );


    /*
        اطلاعات نماد پایه
    */
    setSpreadReportValue(
        "report-base-symbol",
        baseReport.symbol
    );

    setSpreadReportValue(
        "report-base-last-price",
        baseReport.lastPrice
    );

    setSpreadReportValue(
        "report-base-close-price",
        baseReport.closePrice
    );


    /*
        اطلاعات نماد خرید
    */
    setSpreadReportValue(
        "report-buy-symbol",
        buyReport.symbol
    );

    setSpreadReportValue(
        "report-buy-open-interest",
        buyReport.openInterest
    );

    setSpreadReportValue(
        "report-buy-status",
        buyReport.status
    );

    setSpreadReportValue(
        "report-buy-last-price",
        buyReport.lastPrice
    );

    setSpreadReportValue(
        "report-buy-close-price",
        buyReport.closePrice
    );

    setSpreadReportValue(
        "report-buy-trade-value",
        buyReport.tradeValue
    );

    setSpreadReportValue(
        "report-buy-trade-volume",
        buyReport.tradeVolume
    );


    /*
        اطلاعات نماد فروش
    */
    setSpreadReportValue(
        "report-sell-symbol",
        sellReport.symbol
    );

    setSpreadReportValue(
        "report-sell-open-interest",
        sellReport.openInterest
    );

    setSpreadReportValue(
        "report-sell-status",
        sellReport.status
    );

    setSpreadReportValue(
        "report-sell-last-price",
        sellReport.lastPrice
    );

    setSpreadReportValue(
        "report-sell-close-price",
        sellReport.closePrice
    );

    setSpreadReportValue(
        "report-sell-trade-value",
        sellReport.tradeValue
    );

    setSpreadReportValue(
        "report-sell-trade-volume",
        sellReport.tradeVolume
    );


    /*
        جداول سفارشات
    */
    renderOrderBookTable(
        "buy-orderbook-table",
        buyOrderBook
    );


    renderOrderBookTable(
        "sell-orderbook-table",
        sellOrderBook
    );

    renderSpreadPayoffChart(
        row
    );


}

function hideSpreadOrderBooks() {

    const box =
        document.getElementById(
            "spread-orderbook-box"
        );

    if (box) {
        box.style.display =
            "none";
    }
}

function renderSpreadCalculationTable(
    data,
    rebuildControls = true
) {

    const tableHead = document.querySelector(
        "#spread-calculation-table thead"
    );

    const tableBody = document.querySelector(
        "#spread-calculation-table tbody"
    );

    if (!tableHead || !tableBody) {
        return;
    }


    tableHead.innerHTML = "";
    tableBody.innerHTML = "";


    if (
        !Array.isArray(data) ||
        data.length === 0
    ) {

        tableBody.innerHTML = `
            <tr>
                <td>
                    ترکیب اسپردی مطابق شرایط موجود نیست.
                </td>
            </tr>
        `;

        return;
    }


    /*
        تمام ستون‌های واقعی جدول
    */
    const allHeaders =
        Object
            .keys(data[0])
            .filter(header =>
                !header.startsWith("__")
            );


    /*
        در صورت نیاز checkboxها ساخته شوند.
    */
    if (rebuildControls) {

        renderSpreadColumnControls(
            allHeaders
        );
    }


    /*
        فقط ستون‌هایی که تیک دارند
        وارد جدول می‌شوند.
    */
    const visibleHeaders =
        allHeaders.filter(
            header =>
                !hiddenSpreadCalculationColumns.has(
                    header
                )
        );


    /*
        اگر کاربر همه ستون‌ها را مخفی کرده باشد
    */
    if (visibleHeaders.length === 0) {

        tableBody.innerHTML = `
            <tr>
                <td>
                    هیچ ستونی برای نمایش انتخاب نشده است.
                </td>
            </tr>
        `;

        return;
    }


    /*
        ساخت ردیف عنوان
    */
    const headRow =
        document.createElement("tr");


    visibleHeaders.forEach(header => {

        const th =
            document.createElement("th");

        let sortIcon = "";


        if (
            spreadCalculationSort.column ===
            header
        ) {

            if (
                spreadCalculationSort.direction ===
                "desc"
            ) {
                sortIcon = " ▼";
            }

            if (
                spreadCalculationSort.direction ===
                "asc"
            ) {
                sortIcon = " ▲";
            }
        }


        th.textContent =
            header + sortIcon;


        th.addEventListener(
            "click",
            function () {

                sortSpreadCalculationTable(
                    header
                );
            }
        );


        headRow.appendChild(
            th
        );
    });


    tableHead.appendChild(
        headRow
    );


    /*
        ساخت ردیف‌های جدول
    */
    data.forEach((row, index) => {

        const tr =
            document.createElement("tr");


        /*
            حفظ قابلیت انتخاب ردیف
            که قبلاً اضافه کردیم
        */
        const rowKey =
            getTableRowKey(
                "spreadCalculation",
                row,
                index
            );


        applyRowSelection({

            tableName:
                "spreadCalculation",

            tableSelector:
                "#spread-calculation-table",

            rowElement:
                tr,

            rowKey
        });

        /*
            کلیک روی ردیف =
            نمایش Order Book خرید و فروش
        */
        tr.addEventListener(
            "click",
            function () {

                showSpreadOrderBooks(
                    row
                );
            }
        );

        /*
            فقط ستون‌های تیک‌خورده
            ساخته می‌شوند.
        */
        visibleHeaders.forEach(header => {

            const td =
                document.createElement("td");

            td.classList.add(
                "number-cell"
            );

            td.textContent =
                row[header] ?? "";

            tr.appendChild(
                td
            );
        });


        tableBody.appendChild(
            tr
        );
    });
}

function sortSpreadCalculationTable(column) {

    /*
        کلیک اول: نزولی
        کلیک دوم: صعودی
        کلیک سوم: ترتیب اولیه
    */
    if (
        spreadCalculationSort.column !== column
    ) {

        spreadCalculationSort = {
            column: column,
            direction: "desc"
        };

    } else if (
        spreadCalculationSort.direction === "desc"
    ) {

        spreadCalculationSort.direction =
            "asc";

    } else {

        spreadCalculationSort = {
            column: null,
            direction: null
        };

        spreadCalculationCurrentData = [
            ...spreadCalculationOriginalData
        ];

        renderSpreadCalculationTable(
            spreadCalculationCurrentData,
            false
        );

        return;
    }

    const sortedData = [
        ...spreadCalculationOriginalData
    ];

    sortedData.sort((rowA, rowB) => {

        let valueA =
            normalizeSpreadSortValue(
                rowA[column]
            );

        let valueB =
            normalizeSpreadSortValue(
                rowB[column]
            );

        /*
            قراردادن مقادیر خالی در انتهای جدول
        */
        const emptyA =
            valueA === "" ||
            valueA === null ||
            valueA === undefined;

        const emptyB =
            valueB === "" ||
            valueB === null ||
            valueB === undefined;

        if (emptyA && emptyB) {
            return 0;
        }

        if (emptyA) {
            return 1;
        }

        if (emptyB) {
            return -1;
        }

        if (valueA < valueB) {
            return (
                spreadCalculationSort.direction ===
                "asc"
            ) ? -1 : 1;
        }

        if (valueA > valueB) {
            return (
                spreadCalculationSort.direction ===
                "asc"
            ) ? 1 : -1;
        }

        return 0;
    });

    spreadCalculationCurrentData =
        sortedData;

    renderSpreadCalculationTable(
        spreadCalculationCurrentData,
        false
    );
}

function resetSpreadCalculationTable() {

    hideSpreadOrderBooks();

    spreadCalculationOriginalData = [];

    spreadCalculationCurrentData = [];

    spreadCalculationSort = {
        column: null,
        direction: null
    };


    /*
        مخفی‌شدن کل بخش محاسبات
    */
    const calculationSection =
        document.getElementById(
            "spread-calculation-section"
        );

    if (calculationSection) {

        calculationSection.style.display =
            "none";
    }


    const tableHead =
        document.querySelector(
            "#spread-calculation-table thead"
        );

    const tableBody =
        document.querySelector(
            "#spread-calculation-table tbody"
        );


    if (tableHead) {

        tableHead.innerHTML = "";

    }


    if (tableBody) {

        tableBody.innerHTML = "";

    }
}

async function loadDiscoveredOptionBases() {
    try {
        const response = await fetch(`/option-bases?_ts=${Date.now()}`, {
            cache: "no-store"
        });
        const result = await response.json();
        if (!response.ok) {
            return;
        }

        discoveredBaseSymbols = Array.isArray(result.bases)
            ? result.bases.map(normalizeSymbol)
            : [];

        if (result.mapping && typeof result.mapping === "object") {
            Object.entries(result.mapping).forEach(([root, base]) => {
                mapping[normalizeSymbol(root)] = normalizeSymbol(base);
            });
        }
    } catch (error) {
        console.error("Option base discovery error:", error);
    }
}

function formatExpectationNumber(value, digits = 0) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
        return "—";
    }
    return Number(value).toLocaleString("fa-IR", {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits
    });
}

function formatExpectationPercent(value, digits = 2) {
    if (value === null || value === undefined) {
        return "—";
    }
    return `${formatExpectationNumber(value, digits)}٪`;
}

function formatExpectationTimestamp(value) {
    if (!value) {
        return "—";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return "—";
    }

    return new Intl.DateTimeFormat("fa-IR", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        timeZone: "Asia/Tehran"
    }).format(date);
}

function renderMarketExpectations(payload) {
    const list = document.getElementById("expectations-list");
    const empty = document.getElementById("expectations-empty");
    if (!list || !empty) {
        return;
    }

    const openBaseSymbols = new Set(
        [...list.querySelectorAll(".expectations-base[open]")]
            .map(item => item.dataset.baseSymbol)
    );
    const bases = Array.isArray(payload?.bases) ? payload.bases : [];
    const nextList = document.createDocumentFragment();
    const summaryButton = document.getElementById("nearest-expiry-summary");
    if (summaryButton) summaryButton.disabled = bases.length === 0;
    const expiringButton = document.getElementById("show-expiring-options");
    if (expiringButton) expiringButton.disabled = bases.length === 0;
    const marketShareButton = document.getElementById("show-market-share-options");
    if (marketShareButton) marketShareButton.disabled = bases.length === 0;
    const generatedTime = formatExpectationTimestamp(payload?.generated_at);
    const sourceLabel = payload?.trade_value_source === "snapshot"
        ? "ذخیره روز قبل"
        : "داده زنده";
    const meta = document.getElementById("expectations-meta");
    const connection = document.getElementById("market-connection");
    const connectionTime = document.getElementById("market-connection-time");

    if (meta) {
        meta.textContent = `آخرین محاسبه ${generatedTime} · منبع ارزش معاملات: ${sourceLabel}`;
    }

    if (connection) {
        connection.classList.add("is-live");
        connection.classList.remove("has-error");
    }

    if (connectionTime) {
        connectionTime.textContent = generatedTime;
        connectionTime.dateTime = payload?.generated_at || "";
    }

    bases.forEach((base, baseIndex) => {
        const details = document.createElement("details");
        details.className = "expectations-base";
        details.dataset.baseSymbol = normalizeSymbol(base.base_symbol);
        details.open = openBaseSymbols.has(details.dataset.baseSymbol);

        const groups = Array.isArray(base.groups) ? base.groups : [];
        const nearestGroup = [...groups].sort((first, second) =>
            Number(first.days_remaining) - Number(second.days_remaining)
        )[0];
        const nearestWeightedAverage = Number(nearestGroup?.weighted_average);
        const nearestWeightedTone = (
            Number.isFinite(nearestWeightedAverage)
            && nearestWeightedAverage < 0
        ) ? "is-negative" : "is-positive";

        const summary = document.createElement("summary");
        summary.innerHTML = `
            <span class="expectations-symbol-block">
                <span class="expectations-symbol">${base.base_symbol}</span>
                <small class="expectations-count">${formatExpectationNumber(groups.length)} سررسید فعال</small>
            </span>
            <span class="expectations-glance">
                <span>
                    <span class="expectations-glance-label">نزدیک‌ترین سررسید:</span>
                    <strong>${nearestGroup?.expiry_date || "—"}</strong>
                </span>
                <span>
                    <span class="expectations-glance-label">روز باقی‌مانده:</span>
                    <strong>${formatExpectationNumber(nearestGroup?.days_remaining)}</strong>
                </span>
                <span>
                    <span class="expectations-glance-label">میانگین وزنی نزدیک‌ترین سررسید:</span>
                    <strong class="expectation-weighted ${nearestWeightedTone}">${formatExpectationPercent(nearestGroup?.weighted_average)}</strong>
                </span>
            </span>
            <span class="expectations-chevron" aria-hidden="true"></span>`;
        details.appendChild(summary);

        const wrapper = document.createElement("div");
        wrapper.className = "expectations-table-wrap";
        const table = document.createElement("table");
        table.className = "expectations-table";
        table.innerHTML = `
            <thead><tr>
                <th>روز تا سررسید</th>
                <th>تاریخ سررسید</th>
                <th>مینیمم فاصله تا سر‌به‌سر</th>
                <th>ماکسیمم فاصله تا سر‌به‌سر</th>
                <th>میانگین وزنی</th>
                <th>جزئیات</th>
            </tr></thead>
            <tbody></tbody>`;

        const tbody = table.querySelector("tbody");
        groups.forEach(group => {
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${formatExpectationNumber(group.days_remaining)}</td>
                <td>${group.expiry_date || "—"}</td>
                <td class="expectation-percent">${formatExpectationPercent(group.minimum)}</td>
                <td class="expectation-percent">${formatExpectationPercent(group.maximum)}</td>
                <td class="expectation-percent expectation-weighted">${formatExpectationPercent(group.weighted_average)}</td>
                <td><button type="button" class="expectations-detail-link" data-base-index="${baseIndex}" data-group-id="${group.group_id}">مشاهده محاسبات</button></td>`;
            tbody.appendChild(row);
        });

        wrapper.appendChild(table);
        details.appendChild(wrapper);
        nextList.appendChild(details);
        initializeExpectationAccordion(details, summary, wrapper);
    });

    list.replaceChildren(nextList);
    empty.hidden = bases.length > 0;
    list.hidden = bases.length === 0;

    filterMarketExpectationSymbols(
        document.getElementById("expectations-search")?.value || "",
        payload
    );
}

function filterMarketExpectationSymbols(
    searchValue,
    data = marketExpectationsData
) {
    const query = normalizeSymbol(searchValue).toLocaleLowerCase("fa");
    let visibleCount = 0;

    document.querySelectorAll(".expectations-base").forEach(item => {
        const symbol = (item.dataset.baseSymbol || "").toLocaleLowerCase("fa");
        const visible = !query || symbol.includes(query);
        item.hidden = !visible;
        if (visible) visibleCount += 1;
    });

    const empty = document.getElementById("expectations-empty");
    const list = document.getElementById("expectations-list");
    if (empty && list && data?.bases?.length) {
        empty.hidden = visibleCount > 0;
        empty.textContent = visibleCount > 0
            ? ""
            : "نمادی مطابق عبارت جست‌وجو پیدا نشد.";
    }
}

function initializeExpectationAccordion(details, summary, content) {
    summary.addEventListener("click", event => {
        event.preventDefault();
        if (details.dataset.animating === "true") return;

        details.dataset.animating = "true";
        const isOpen = details.open;

        if (!isOpen) {
            details.open = true;
        }

        const animation = content.animate(
            isOpen
                ? [
                    { height: `${content.scrollHeight}px`, opacity: 1 },
                    { height: "0px", opacity: 0 }
                ]
                : [
                    { height: "0px", opacity: 0 },
                    { height: `${content.scrollHeight}px`, opacity: 1 }
                ],
            { duration: 280, easing: "cubic-bezier(.22,.8,.3,1)" }
        );

        animation.onfinish = () => {
            if (isOpen) details.open = false;
            content.style.height = "";
            content.style.opacity = "";
            details.dataset.animating = "false";
        };
        animation.oncancel = animation.onfinish;
    });
}

async function loadMarketExpectations(force = false) {
    if (marketExpectationsLoading || (marketExpectationsData && !force)) {
        return;
    }

    const loading = document.getElementById("expectations-loading");
    const list = document.getElementById("expectations-list");
    const empty = document.getElementById("expectations-empty");
    const refreshButton = document.getElementById("refresh-expectations");
    const connection = document.getElementById("market-connection");
    const connectionTime = document.getElementById("market-connection-time");
    const hasRenderedData = Boolean(
        list
        && list.childElementCount > 0
        && !list.hidden
    );
    marketExpectationsLoading = true;
    const summaryButton = document.getElementById("nearest-expiry-summary");
    if (summaryButton && !hasRenderedData) summaryButton.disabled = true;
    const expiringButton = document.getElementById("show-expiring-options");
    if (expiringButton && !hasRenderedData) expiringButton.disabled = true;
    const marketShareButton = document.getElementById("show-market-share-options");
    if (marketShareButton && !hasRenderedData) {
        marketShareButton.disabled = true;
    }
    if (loading) {
        loading.hidden = hasRenderedData;
        if (!hasRenderedData) {
            loading.textContent = "در حال دریافت و محاسبه اطلاعات...";
        }
    }
    if (list) {
        list.hidden = !hasRenderedData;
        if (hasRenderedData) {
            list.setAttribute("aria-busy", "true");
        }
    }
    if (empty && !hasRenderedData) {
        empty.hidden = true;
    }
    if (refreshButton) {
        refreshButton.classList.add("is-refreshing");
        refreshButton.setAttribute("aria-busy", "true");
    }
    if (connection) {
        connection.classList.remove("is-live", "has-error");
    }
    if (connectionTime) {
        connectionTime.textContent = "در حال دریافت";
        connectionTime.removeAttribute("datetime");
    }

    try {
        const useSavedValue = document
            .getElementById("expectations-use-saved-value")
            ?.checked === true;
        const parameters = new URLSearchParams({
            use_saved_value: useSavedValue ? "1" : "0",
            _ts: Date.now().toString()
        });
        const response = await fetch(`/market-expectations?${parameters.toString()}`, {
            cache: "no-store"
        });
        const responseText = await response.text();
        let result;

        try {
            result = JSON.parse(responseText);
        } catch (parseError) {
            throw new Error(
                response.status === 404
                    ? "مسیر انتظارات بازار روی سرور فعال نیست؛ برنامه پایتون را متوقف و دوباره اجرا کنید."
                    : "سرور به‌جای JSON پاسخ نامعتبر برگرداند. لطفاً برنامه پایتون را مجدداً اجرا کنید."
            );
        }
        if (!response.ok) {
            throw new Error(result.error || "دریافت اطلاعات ناموفق بود.");
        }
        renderMarketExpectations(result);
        marketExpectationsData = result;
        if (loading) loading.hidden = true;
    } catch (error) {
        if (loading) {
            loading.hidden = hasRenderedData;
            if (!hasRenderedData) {
                loading.textContent = error.message || "دریافت اطلاعات ناموفق بود.";
            }
        }
        if (connection) {
            connection.classList.remove("is-live");
            connection.classList.add("has-error");
        }
        if (connectionTime) {
            connectionTime.textContent = hasRenderedData
                ? "نمایش آخرین داده"
                : "خطا در اتصال";
        }
    } finally {
        marketExpectationsLoading = false;
        if (list) {
            list.removeAttribute("aria-busy");
        }
        if (refreshButton) {
            refreshButton.classList.remove("is-refreshing");
            refreshButton.removeAttribute("aria-busy");
        }
    }
}

function startMarketExpectationsAutoRefresh() {
    if (marketExpectationsRefreshTimer) {
        clearInterval(marketExpectationsRefreshTimer);
    }

    marketExpectationsRefreshTimer = setInterval(() => {
        loadMarketExpectations(true);
    }, DASHBOARD_AUTO_REFRESH_INTERVAL);
}

function openNearestExpirySummary() {
    const modal = document.getElementById("nearest-expiry-modal");
    const tbody = modal?.querySelector(".nearest-expiry-table tbody");
    const bases = marketExpectationsData?.bases;
    if (!modal || !tbody || !Array.isArray(bases)) {
        return;
    }

    const nearestGroups = bases.map((base, baseIndex) => {
        const validGroups = Array.isArray(base.groups)
            ? base.groups.filter(group =>
                Number.isFinite(Number(group.days_remaining))
                && Number(group.days_remaining) >= 0
            )
            : [];
        if (!validGroups.length) return null;

        const nearestGroup = validGroups.reduce((nearest, current) => (
            Number(current.days_remaining) < Number(nearest.days_remaining)
                ? current
                : nearest
        ));
        return { base, baseIndex, group: nearestGroup };
    }).filter(Boolean).sort((first, second) =>
        String(first.base.base_symbol).localeCompare(
            String(second.base.base_symbol),
            "fa",
            { sensitivity: "base" }
        )
    );

    tbody.innerHTML = nearestGroups.map(({ base, baseIndex, group }) => `
        <tr>
            <td class="nearest-expiry-symbol" data-sort-value="${base.base_symbol}">${base.base_symbol}</td>
            <td data-sort-value="${group.days_remaining}">${formatExpectationNumber(group.days_remaining)}</td>
            <td data-sort-value="${group.expiry_date || ""}">${group.expiry_date || "—"}</td>
            <td class="expectation-percent" data-sort-value="${group.minimum ?? ""}">${formatExpectationPercent(group.minimum)}</td>
            <td class="expectation-percent" data-sort-value="${group.maximum ?? ""}">${formatExpectationPercent(group.maximum)}</td>
            <td class="expectation-percent expectation-weighted" data-sort-value="${group.weighted_average ?? ""}">${formatExpectationPercent(group.weighted_average)}</td>
            <td>
                <button type="button" class="expectations-detail-link nearest-expiry-detail-link" data-base-index="${baseIndex}" data-group-id="${group.group_id}">
                    مشاهده محاسبات
                </button>
            </td>
        </tr>
    `).join("");

    resetExpectationSummarySort(modal.querySelector(".nearest-expiry-table"));

    modal.hidden = false;
    document.body.classList.add("expectations-modal-open");
}

function closeNearestExpirySummary() {
    const modal = document.getElementById("nearest-expiry-modal");
    if (modal) modal.hidden = true;
    syncExpectationModalBodyState();
}

function openExpiringOptionsSummary() {
    const minimumInput = document.getElementById("expectations-min-days");
    const maximumInput = document.getElementById("expectations-max-days");
    const minimumDays = minimumInput?.value.trim() === ""
        ? 0
        : Number(minimumInput?.value);
    const maximumDays = Number(maximumInput?.value);

    if (!Number.isFinite(minimumDays) || minimumDays < 0) {
        minimumInput?.setCustomValidity("لطفاً یک عدد صفر یا بزرگ‌تر وارد کنید.");
        minimumInput?.reportValidity();
        return;
    }
    if (!maximumInput || maximumInput.value.trim() === ""
        || !Number.isFinite(maximumDays) || maximumDays < 0) {
        maximumInput?.setCustomValidity("لطفاً یک عدد صفر یا بزرگ‌تر وارد کنید.");
        maximumInput?.reportValidity();
        return;
    }
    if (minimumDays > maximumDays) {
        maximumInput.setCustomValidity("مقدار «تا روز» باید بزرگ‌تر یا مساوی «از روز» باشد.");
        maximumInput.reportValidity();
        return;
    }
    minimumInput?.setCustomValidity("");
    maximumInput.setCustomValidity("");

    const modal = document.getElementById("expiring-options-modal");
    const tbody = modal?.querySelector(".expiring-options-table tbody");
    const bases = marketExpectationsData?.bases;
    if (!modal || !tbody || !Array.isArray(bases)) return;

    const matches = [];
    bases.forEach((base, baseIndex) => {
        (base.groups || []).forEach(group => {
            const days = Number(group.days_remaining);
            if (Number.isFinite(days) && days >= minimumDays && days <= maximumDays) {
                matches.push({ base, baseIndex, group });
            }
        });
    });
    matches.sort((first, second) =>
        Number(first.group.days_remaining) - Number(second.group.days_remaining)
        || String(first.base.base_symbol).localeCompare(String(second.base.base_symbol), "fa")
    );

    document.getElementById("expiring-options-modal-title").textContent =
        `سررسیدهای از ${formatExpectationNumber(minimumDays)} تا ${formatExpectationNumber(maximumDays)} روز`;
    tbody.innerHTML = matches.length
        ? matches.map(({ base, baseIndex, group }) => `
            <tr>
                <td class="nearest-expiry-symbol" data-sort-value="${base.base_symbol}">${base.base_symbol}</td>
                <td data-sort-value="${group.days_remaining}">${formatExpectationNumber(group.days_remaining)}</td>
                <td data-sort-value="${group.expiry_date || ""}">${group.expiry_date || "—"}</td>
                <td class="expectation-percent" data-sort-value="${group.minimum ?? ""}">${formatExpectationPercent(group.minimum)}</td>
                <td class="expectation-percent" data-sort-value="${group.maximum ?? ""}">${formatExpectationPercent(group.maximum)}</td>
                <td class="expectation-percent expectation-weighted" data-sort-value="${group.weighted_average ?? ""}">${formatExpectationPercent(group.weighted_average)}</td>
                <td><button type="button" class="expectations-detail-link expiring-option-detail-link" data-base-index="${baseIndex}" data-group-id="${group.group_id}">مشاهده محاسبات</button></td>
            </tr>`).join("")
        : `<tr><td colspan="7" class="expectations-no-result">سررسیدی در این بازه پیدا نشد.</td></tr>`;

    resetExpectationSummarySort(modal.querySelector(".expiring-options-table"));
    modal.hidden = false;
    document.body.classList.add("expectations-modal-open");
}

function closeExpiringOptionsSummary() {
    const modal = document.getElementById("expiring-options-modal");
    if (modal) modal.hidden = true;
    syncExpectationModalBodyState();
}

function openMarketShareOptionsSummary() {
    const input = document.getElementById("expectations-market-share-count");
    const requestedCount = Number(input?.value);
    if (!Number.isInteger(requestedCount) || requestedCount <= 0) {
        input?.setCustomValidity("تعداد باید یک عدد صحیح بزرگ‌تر از صفر باشد.");
        input?.reportValidity();
        return;
    }

    const modal = document.getElementById("market-share-options-modal");
    const tbody = modal?.querySelector(".market-share-options-table tbody");
    const bases = marketExpectationsData?.bases;
    if (!modal || !tbody || !Array.isArray(bases)) return;

    const options = bases.flatMap(base =>
        (base.groups || []).flatMap(group =>
            (group.options || []).map(option => ({
                ...option,
                base_symbol: base.base_symbol
            }))
        )
    ).sort((first, second) =>
        Number(second.market_trade_value_share || 0)
        - Number(first.market_trade_value_share || 0)
    ).slice(0, requestedCount);

    document.getElementById("market-share-options-modal-title").textContent =
        `${formatExpectationNumber(requestedCount)} نماد برتر از نظر سهم ارزش معاملات`;
    tbody.innerHTML = options.length
        ? options.map((option, index) => `
            <tr>
                <td data-sort-value="${index + 1}">${formatExpectationNumber(index + 1)}</td>
                <td data-sort-value="${option.symbol || ""}">${option.symbol || "—"}</td>
                <td data-sort-value="${option.base_symbol || ""}">${option.base_symbol || "—"}</td>
                <td data-sort-value="${option.days_remaining ?? ""}">${formatExpectationNumber(option.days_remaining)}</td>
                <td data-sort-value="${option.trade_value ?? ""}">${formatExpectationNumber(Number(option.trade_value) / 1_000_000, 1)}</td>
                <td class="expectation-percent" data-sort-value="${option.market_trade_value_share ?? ""}">${formatExpectationPercent(option.market_trade_value_share, 4)}</td>
                <td class="expectation-percent" data-sort-value="${option.breakeven_distance ?? ""}">${formatExpectationPercent(option.breakeven_distance)}</td>
                <td class="expectation-percent" data-sort-value="${option.monthly_return ?? ""}">${formatExpectationPercent(option.monthly_return)}</td>
            </tr>`).join("")
        : `<tr><td colspan="8" class="expectations-no-result">اطلاعاتی برای نمایش وجود ندارد.</td></tr>`;

    resetExpectationSummarySort(modal.querySelector(".market-share-options-table"));
    modal.hidden = false;
    document.body.classList.add("expectations-modal-open");
}

function closeMarketShareOptionsSummary() {
    const modal = document.getElementById("market-share-options-modal");
    if (modal) modal.hidden = true;
    syncExpectationModalBodyState();
}

function resetExpectationSummarySort(table) {
    if (!table) return;
    table.dataset.sortColumn = "";
    table.dataset.sortDirection = "asc";
    table.querySelectorAll("th[data-sort-type]").forEach(header => {
        header.setAttribute("aria-sort", "none");
        const indicator = header.querySelector(".expectations-sort-indicator");
        if (indicator) indicator.textContent = "↕";
    });
}

function sortExpectationSummaryTable(table, header) {
    if (!table || !header) return;
    const columnIndex = header.cellIndex;
    const previousColumn = table.dataset.sortColumn;
    const direction = previousColumn === String(columnIndex)
        && table.dataset.sortDirection === "asc" ? "desc" : "asc";
    const rows = [...table.querySelectorAll("tbody tr")]
        .filter(row => row.children.length > 1);

    rows.sort((firstRow, secondRow) => {
        const firstValue = firstRow.children[columnIndex]?.dataset.sortValue ?? "";
        const secondValue = secondRow.children[columnIndex]?.dataset.sortValue ?? "";
        if (firstValue === "" && secondValue !== "") return 1;
        if (secondValue === "" && firstValue !== "") return -1;

        const comparison = header.dataset.sortType === "number"
            ? Number(firstValue) - Number(secondValue)
            : firstValue.localeCompare(secondValue, "fa", { numeric: true, sensitivity: "base" });
        return direction === "asc" ? comparison : -comparison;
    });

    const tbody = table.querySelector("tbody");
    rows.forEach(row => tbody.appendChild(row));
    table.dataset.sortColumn = String(columnIndex);
    table.dataset.sortDirection = direction;
    table.querySelectorAll("th[data-sort-type]").forEach(item => {
        const active = item === header;
        item.setAttribute("aria-sort", active
            ? (direction === "asc" ? "ascending" : "descending")
            : "none");
        const indicator = item.querySelector(".expectations-sort-indicator");
        if (indicator) indicator.textContent = active
            ? (direction === "asc" ? "▲" : "▼") : "↕";
    });
}

function syncExpectationModalBodyState() {
    document.body.classList.toggle(
        "expectations-modal-open",
        Boolean(document.querySelector(".expectations-modal:not([hidden])"))
    );
}

function openExpectationDetails(baseIndex, groupId) {
    const base = marketExpectationsData?.bases?.[baseIndex];
    const group = base?.groups?.find(item => item.group_id === groupId);
    const modal = document.getElementById("expectations-modal");
    if (!base || !group || !modal) {
        return;
    }

    document.getElementById("expectations-modal-title").textContent =
        `${base.base_symbol} — ${group.days_remaining} روز تا سررسید`;
    document.getElementById("expectations-modal-summary").innerHTML = `
        <span>میانگین وزنی: <strong>${formatExpectationPercent(group.weighted_average)}</strong></span>
        <span>مینیمم: <strong>${formatExpectationPercent(group.minimum)}</strong></span>
        <span>ماکسیمم: <strong>${formatExpectationPercent(group.maximum)}</strong></span>
        <span>ارزش کل (میلیون ریال): <strong>${formatExpectationNumber(group.total_trade_value / 1_000_000, 1)}</strong></span>`;

    const table = modal.querySelector(".expectations-detail-table");
    table.querySelector("thead").innerHTML = `<tr>
        <th data-sort-key="symbol" tabindex="0">نماد اختیار خرید <span class="expectations-sort-indicator"></span></th>
        <th data-sort-key="days_remaining" tabindex="0">روز تا سررسید <span class="expectations-sort-indicator"></span></th>
        <th data-sort-key="open_interest" tabindex="0">تعداد موقعیت باز <span class="expectations-sort-indicator"></span></th>
        <th data-sort-key="trade_value" tabindex="0">ارزش معاملات (میلیون ریال) <span class="expectations-sort-indicator"></span></th>
        <th data-sort-key="weight" tabindex="0">وزن نسبت به کل <span class="expectations-sort-indicator"></span></th>
        <th data-sort-key="breakeven_distance" tabindex="0">فاصله تا سر‌به‌سر <span class="expectations-sort-indicator"></span></th>
        <th data-sort-key="monthly_return" tabindex="0">بازدهی ماهیانه <span class="expectations-sort-indicator"></span></th>
        <th data-sort-key="leverage" tabindex="0">اهرم <span class="expectations-sort-indicator"></span></th>
        <th data-sort-key="status" tabindex="0">وضعیت <span class="expectations-sort-indicator"></span></th>
        <th data-sort-key="strike" tabindex="0">قیمت اعمال <span class="expectations-sort-indicator"></span></th>
        <th data-sort-key="option_last_price" tabindex="0">آخرین قیمت اختیار <span class="expectations-sort-indicator"></span></th>
    </tr>`;

    expectationDetailRows = Array.isArray(group.options)
        ? [...group.options]
        : [];
    expectationDetailSort = { key: null, direction: "asc" };
    renderExpectationDetailRows();

    modal.hidden = false;
    document.body.classList.add("expectations-modal-open");
}

function renderExpectationDetailRows() {
    const table = document.querySelector(".expectations-detail-table");
    const tbody = table?.querySelector("tbody");
    if (!table || !tbody) return;

    const rows = [...expectationDetailRows];
    const { key, direction } = expectationDetailSort;

    if (key) {
        rows.sort((first, second) => {
            const firstValue = first[key];
            const secondValue = second[key];
            let comparison;

            if (typeof firstValue === "number" && typeof secondValue === "number") {
                comparison = firstValue - secondValue;
            } else {
                comparison = String(firstValue ?? "").localeCompare(
                    String(secondValue ?? ""),
                    "fa",
                    { numeric: true, sensitivity: "base" }
                );
            }

            return direction === "asc" ? comparison : -comparison;
        });
    }

    tbody.innerHTML = rows.map(option => `
        <tr>
            <td>${option.symbol}</td>
            <td>${formatExpectationNumber(option.days_remaining)}</td>
            <td>${formatExpectationNumber(option.open_interest)}</td>
            <td>${formatExpectationNumber(option.trade_value / 1_000_000, 1)}</td>
            <td class="expectation-percent">${formatExpectationPercent(option.weight)}</td>
            <td class="expectation-percent">${formatExpectationPercent(option.breakeven_distance)}</td>
            <td class="expectation-percent">${formatExpectationPercent(option.monthly_return)}</td>
            <td>${formatExpectationNumber(option.leverage, 2)}</td>
            <td><span class="expectation-option-status is-${String(option.status || "").toLowerCase()}">${option.status || "—"}</span></td>
            <td>${formatExpectationNumber(option.strike)}</td>
            <td>${formatExpectationNumber(option.option_last_price)}</td>
        </tr>`).join("");

    table.querySelectorAll("th[data-sort-key]").forEach(header => {
        const active = header.dataset.sortKey === key;
        header.setAttribute(
            "aria-sort",
            active
                ? (direction === "asc" ? "ascending" : "descending")
                : "none"
        );
        const indicator = header.querySelector(".expectations-sort-indicator");
        if (indicator) {
            indicator.textContent = active
                ? (direction === "asc" ? "▲" : "▼")
                : "↕";
        }
    });
}

function sortExpectationDetails(sortKey) {
    expectationDetailSort = {
        key: sortKey,
        direction: expectationDetailSort.key === sortKey
            && expectationDetailSort.direction === "asc"
            ? "desc"
            : "asc"
    };
    renderExpectationDetailRows();
}

function closeExpectationDetails() {
    const modal = document.getElementById("expectations-modal");
    if (modal) modal.hidden = true;
    syncExpectationModalBodyState();
}

function formatWatchMarketCompact(value, unit = "") {
    const number = Number(value);
    if (value === null || value === undefined || !Number.isFinite(number)) {
        return "—";
    }

    const formatted = Math.abs(number) >= 1_000
        ? `${watchMarketNumberFormatter.format(number / 1_000)} هزار`
        : watchMarketNumberFormatter.format(number);
    return `${formatted}${unit ? ` ${unit}` : ""}`;
}

function getWatchMarketSessionMinute(timestamp) {
    const parts = Object.fromEntries(
        watchMarketClockFormatter
            .formatToParts(new Date(Number(timestamp) * 1_000))
            .map(part => [part.type, part.value])
    );
    return Number(parts.hour) * 60 + Number(parts.minute);
}

function renderWatchMarketSeries(series, timestamps, unit) {
    const availableSeries = series.filter(
        item => Array.isArray(item.values) && item.values.length
    );
    if (!availableSeries.length || !Array.isArray(timestamps) || !timestamps.length) {
        return '<div class="watch-market-chart-empty">داده‌ای برای نمایش دریافت نشد.</div>';
    }

    const sessionStart = 9 * 60;
    const sessionEnd = 12 * 60 + 30;
    const length = Math.min(
        timestamps.length,
        ...availableSeries.map(item => item.values.length)
    );
    const sessionMinutes = timestamps
        .slice(0, length)
        .map(getWatchMarketSessionMinute);
    const sessionIndexes = [];
    for (let index = 0; index < length; index += 1) {
        if (
            sessionMinutes[index] >= sessionStart
            && sessionMinutes[index] <= sessionEnd
        ) {
            sessionIndexes.push(index);
        }
    }

    if (!sessionIndexes.length) {
        return '<div class="watch-market-chart-empty">داده‌ای در ساعت معاملات ۰۹:۰۰ تا ۱۲:۳۰ دریافت نشد.</div>';
    }

    const sampleStep = Math.max(1, Math.ceil(sessionIndexes.length / 90));
    const indexes = sessionIndexes.filter(
        (_, position) => position % sampleStep === 0
    );
    if (indexes.at(-1) !== sessionIndexes.at(-1)) {
        indexes.push(sessionIndexes.at(-1));
    }

    const allValues = availableSeries.flatMap(item => indexes.flatMap(index => {
        const value = item.values[index];
        const number = Number(value);
        return value !== null && value !== undefined && Number.isFinite(number)
            ? [number]
            : [];
    }));
    if (!allValues.length) {
        return '<div class="watch-market-chart-empty">داده‌ای برای نمایش دریافت نشد.</div>';
    }

    let minimum = Math.min(...allValues);
    let maximum = Math.max(...allValues);
    if (minimum === maximum) {
        minimum -= 1;
        maximum += 1;
    }
    const rangePadding = (maximum - minimum) * 0.08;
    minimum -= rangePadding;
    maximum += rangePadding;

    const width = 720;
    const height = 225;
    const padding = { top: 16, right: 15, bottom: 32, left: 70 };
    const xForMinute = minute => (
        padding.left
        + (minute - sessionStart)
        * (width - padding.left - padding.right)
        / (sessionEnd - sessionStart)
    );
    const xForIndex = index => xForMinute(sessionMinutes[index]);
    const yForValue = value => (
        padding.top
        + (height - padding.top - padding.bottom)
        * (maximum - value)
        / (maximum - minimum)
    );

    const grid = [0, 0.25, 0.5, 0.75, 1].map(ratio => {
        const value = maximum - (maximum - minimum) * ratio;
        return `
            <line x1="${padding.left}" y1="${yForValue(value)}" x2="${width - padding.right}" y2="${yForValue(value)}"></line>
            <text x="${padding.left - 7}" y="${yForValue(value) + 3}" text-anchor="end">${formatWatchMarketCompact(value)}</text>
        `;
    }).join("");

    const paths = availableSeries.map(item => {
        const points = indexes.flatMap(index => {
            const rawValue = item.values[index];
            const value = Number(rawValue);
            if (
                rawValue === null
                || rawValue === undefined
                || !Number.isFinite(value)
            ) {
                return [];
            }
            return [[xForIndex(index), yForValue(value), index]];
        });
        const path = points.map(
            (point, index) => `${index ? "L" : "M"} ${point[0]} ${point[1]}`
        ).join(" ");
        const pointStep = Math.max(1, Math.ceil(points.length / 12));
        const dots = points.filter(
            (_, index) => index % pointStep === 0 || index === points.length - 1
        ).map(point => `
            <circle cx="${point[0]}" cy="${point[1]}" r="3" fill="${item.color}">
                <title>${item.name}: ${formatWatchMarketCompact(item.values[point[2]], unit)}</title>
            </circle>
        `).join("");
        return `
            <path d="${path}" fill="none" stroke="${item.color}" stroke-width="2.4" vector-effect="non-scaling-stroke"></path>
            ${dots}
        `;
    }).join("");

    const zeroLine = minimum < 0 && maximum > 0
        ? `<line class="watch-market-zero" x1="${padding.left}" y1="${yForValue(0)}" x2="${width - padding.right}" y2="${yForValue(0)}"></line>`
        : "";
    const timeLabels = [
        [sessionStart, "۰۹:۰۰"],
        [(sessionStart + sessionEnd) / 2, "۱۰:۴۵"],
        [sessionEnd, "۱۲:۳۰"]
    ].map(([minute, label]) => `
        <text x="${xForMinute(minute)}" y="${height - 7}" text-anchor="middle">${label}</text>
    `).join("");

    return `
        <svg class="watch-market-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
            <g class="watch-market-grid">${grid}</g>
            ${zeroLine}
            ${paths}
            ${timeLabels}
        </svg>
    `;
}

function renderWatchMarketBars(labels, values, unit, colors) {
    if (!Array.isArray(values) || !values.length) {
        return '<div class="watch-market-chart-empty">داده‌ای برای نمایش دریافت نشد.</div>';
    }

    const numericValues = values.map(value => Number(value) || 0);
    const maximum = Math.max(...numericValues, 1);
    const width = 720;
    const height = 225;
    const padding = { top: 18, right: 12, bottom: 49, left: 40 };
    const slot = (width - padding.left - padding.right) / numericValues.length;
    const barWidth = Math.max(8, slot * 0.62);
    const bars = numericValues.map((value, index) => {
        const barHeight = (height - padding.top - padding.bottom) * value / maximum;
        const x = padding.left + slot * index + (slot - barWidth) / 2;
        const y = height - padding.bottom - barHeight;
        const color = colors[index % colors.length];
        return `
            <rect x="${x}" y="${y}" width="${barWidth}" height="${barHeight}" rx="5" fill="${color}">
                <title>${labels[index] || ""}: ${formatWatchMarketCompact(value, unit)}</title>
            </rect>
            <text x="${x + barWidth / 2}" y="${height - 25}" text-anchor="middle">${labels[index] || ""}</text>
            <text class="watch-market-bar-value" x="${x + barWidth / 2}" y="${Math.max(12, y - 6)}" text-anchor="middle">${formatWatchMarketCompact(value)}</text>
        `;
    }).join("");

    return `
        <svg class="watch-market-svg watch-market-bars" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
            ${bars}
        </svg>
    `;
}

function createWatchMarketChartCard(title, subtitle, legend, body, latest) {
    const legendMarkup = Array.isArray(legend) && legend.length
        ? `
            <div class="watch-market-legend">
                ${legend.map(item => `
                    <span><i style="--legend:${item.color}"></i>${item.name}</span>
                `).join("")}
            </div>
        `
        : "";
    const latestMarkup = latest !== null && latest !== undefined
        ? `<strong>${latest}</strong>`
        : "";
    return `
        <article class="watch-market-chart-card">
            <div class="watch-market-chart-head">
                <div>
                    <h3>${title}</h3>
                    <p>${subtitle}</p>
                </div>
                ${latestMarkup}
            </div>
            ${legendMarkup}
            <div class="watch-market-chart-canvas">${body}</div>
        </article>
    `;
}

function formatWatchMarketPrice(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) return "—";
    const maximumFractionDigits = Math.abs(number) < 100
        ? 2
        : Math.abs(number) < 10_000
            ? 1
            : 0;
    return new Intl.NumberFormat("fa-IR", {
        maximumFractionDigits
    }).format(number);
}

function getWatchMarketDirection(value) {
    const number = Number(value);
    if (!Number.isFinite(number) || number === 0) return "neutral";
    return number > 0 ? "positive" : "negative";
}

function renderWatchMarketOverview() {
    const container = document.getElementById("watch-market-overview");
    if (!container) return;

    const overview = watchMarketData?.overview || {};
    const prices = Array.isArray(overview.prices) ? overview.prices : [];
    const flows = Array.isArray(overview.flows) ? overview.flows : [];
    if (!prices.length && !flows.length) {
        container.hidden = true;
        container.replaceChildren();
        return;
    }

    const priceCards = prices.map(item => {
        const percent = Number(item.change_percent);
        const direction = getWatchMarketDirection(percent);
        const percentMarkup = Number.isFinite(percent)
            ? `<span class="watch-market-metric-change ${direction}">${watchMarketSignedFormatter.format(percent)}٪</span>`
            : '<span class="watch-market-metric-change neutral">بدون تغییر ثبت‌شده</span>';
        const sourceLink = item.source_url
            ? `
                <a
                    class="watch-market-metric-link"
                    href="${escapeHtml(item.source_url)}"
                    target="_blank"
                    rel="noopener"
                    aria-label="مشاهده ${escapeHtml(item.name)} در منبع"
                    title="مشاهده در منبع"
                >↗</a>
            `
            : "";
        return `
            <article class="watch-market-metric-card" data-tone="${escapeHtml(item.tone || "currency")}">
                <header>
                    <span>${escapeHtml(item.name || "")}</span>
                    ${sourceLink}
                </header>
                <strong>${formatWatchMarketPrice(item.price)}</strong>
                <footer>
                    <small>${escapeHtml(item.unit || "")}</small>
                    ${percentMarkup}
                </footer>
            </article>
        `;
    }).join("");

    const flowCards = flows.map(item => {
        const value = Number(item.value);
        const hasValue = Number.isFinite(value);
        const direction = getWatchMarketDirection(value);
        const flowLabel = !hasValue || value === 0
            ? "خنثی"
            : value > 0
                ? "ورود پول"
                : "خروج پول";
        const count = Number(item.count);
        const detail = Number.isFinite(count) && count > 0
            ? `${watchMarketNumberFormatter.format(count)} صندوق`
            : escapeHtml(item.market_date || "آخرین داده بازار");
        return `
            <article class="watch-market-flow-card ${direction}">
                <header>
                    <span>${escapeHtml(item.name || "")}</span>
                    <em>${flowLabel}</em>
                </header>
                <strong>${hasValue ? watchMarketSignedFormatter.format(value) : "—"}</strong>
                <footer>
                    <small>میلیارد تومان</small>
                    <span>${detail}</span>
                </footer>
            </article>
        `;
    }).join("");

    container.innerHTML = `
        ${prices.length ? `
            <section class="watch-market-overview-group" aria-labelledby="watch-market-prices-title">
                <div class="watch-market-overview-title">
                    <h3 id="watch-market-prices-title">قیمت‌های کلیدی</h3>
                    <span>آخرین معامله و تغییر روزانه</span>
                </div>
                <div class="watch-market-metric-grid">${priceCards}</div>
            </section>
        ` : ""}
        ${flows.length ? `
            <section class="watch-market-overview-group" aria-labelledby="watch-market-flows-title">
                <div class="watch-market-overview-title">
                    <h3 id="watch-market-flows-title">جریان پول</h3>
                    <span>عدد مثبت ورود و عدد منفی خروج پول است</span>
                </div>
                <div class="watch-market-flow-grid">${flowCards}</div>
            </section>
        ` : ""}
    `;
    container.hidden = false;
}

function updateWatchMarketStatus() {
    const status = document.getElementById("watch-market-status");
    if (!status) return;

    const fetchedAt = Number(watchMarketData?.fetched_at);
    const dateLabel = Number.isFinite(fetchedAt) && fetchedAt > 0
        ? new Date(fetchedAt * 1_000).toLocaleString("fa-IR")
        : "نامشخص";
    const hasErrors = watchMarketData?.errors?.length
        || watchMarketData?.overview?.errors?.length;
    const prefix = hasErrors
        ? "نمایش آخرین داده ذخیره‌شده"
        : "آخرین دریافت";
    const sourceLink = (href, label) => {
        const link = document.createElement("a");
        link.href = href;
        link.target = "_blank";
        link.rel = "noopener";
        link.textContent = label;
        return link;
    };
    status.replaceChildren(
        document.createTextNode(`${prefix}: ${dateLabel} • منابع: `),
        sourceLink("https://tradersarena.ir/", "TradersArena"),
        document.createTextNode("، "),
        sourceLink("https://rahavard365.com/", "ره‌آورد۳۶۵"),
        document.createTextNode(" و "),
        sourceLink("https://finance.yahoo.com/quote/HG=F/", "Yahoo Finance")
    );
}

function renderWatchMarketCharts() {
    const container = document.getElementById("watch-market-charts");
    const empty = document.getElementById("watch-market-empty");
    if (!container || !empty) return;

    renderWatchMarketOverview();
    const charts = watchMarketData?.charts || {};
    const timestamps = watchMarketData?.times || [];
    if (!Object.keys(charts).length) {
        container.hidden = true;
        empty.hidden = false;
        updateWatchMarketStatus();
        return;
    }

    const green = "#4cf19a";
    const red = "#ff7a72";
    const cyan = "#32d9ff";
    const violet = "#a78bfa";
    const yellow = "#fbbf24";
    const orderFlow = charts.order_flow || {};
    const moneyFlow = charts.money_flow || {};
    const breadth = charts.breadth || {};
    const priceRange = charts.price_range || {};
    const orderSnapshot = charts.order_snapshot || {};
    const excitement = charts.excitement || {};
    const rangeLabels = [
        "≤−۵",
        "−۵ - −۴",
        "−۴ - −۳",
        "−۳ - −۲",
        "−۲ - −۱",
        "−۱ - ۰",
        "۰ - +۱",
        "+۱ - +۲",
        "+۲ - +۳",
        "+۳ - +۴",
        "+۴ - +۵",
        "≥+۵"
    ];
    const lastValue = values => (
        Array.isArray(values) && values.length ? values.at(-1) : null
    );
    const latestMoneyFlow = lastValue(moneyFlow.values);
    const latestExcitement = lastValue(excitement.values);

    container.innerHTML = [
        createWatchMarketChartCard(
            "ارزش سفارش‌های خرید و فروش",
            "سهام، حق تقدم و صندوق‌های سهامی • پنج ردیف اول بازار",
            [
                { name: "خرید", color: green },
                { name: "فروش", color: red }
            ],
            renderWatchMarketSeries(
                [
                    { name: "خرید", values: orderFlow.buy, color: green },
                    { name: "فروش", values: orderFlow.sell, color: red }
                ],
                timestamps,
                orderFlow.unit
            ),
            null
        ),
        createWatchMarketChartCard(
            "محدوده قیمتی آخرین معاملات",
            "توزیع نمادهای سهام، حق تقدم و صندوق‌های سهامی",
            null,
            renderWatchMarketBars(
                rangeLabels.slice(0, priceRange.values?.length || 0),
                priceRange.values,
                priceRange.unit,
                [
                    red,
                    red,
                    red,
                    "#f97316",
                    "#fb923c",
                    yellow,
                    "#bef264",
                    "#86efac",
                    green,
                    green,
                    green,
                    cyan
                ]
            ),
            `${formatWatchMarketCompact(
                (priceRange.values || []).reduce(
                    (sum, value) => sum + Number(value || 0),
                    0
                )
            )} نماد`
        ),
        createWatchMarketChartCard(
            "ورود پول به سهام",
            "سهام، حق تقدم و صندوق‌های سهامی؛ مثبت به معنی ورود پول",
            null,
            renderWatchMarketSeries(
                [
                    {
                        name: "خالص ورود پول",
                        values: moneyFlow.values,
                        color: cyan
                    }
                ],
                timestamps,
                moneyFlow.unit
            ),
            formatWatchMarketCompact(latestMoneyFlow, moneyFlow.unit)
        ),
        createWatchMarketChartCard(
            "نمادهای مثبت و منفی",
            "سهام، حق تقدم و صندوق‌های سهامی",
            [
                { name: "مثبت", color: green },
                { name: "منفی", color: red }
            ],
            renderWatchMarketSeries(
                [
                    {
                        name: "مثبت",
                        values: breadth.positive,
                        color: green
                    },
                    {
                        name: "منفی",
                        values: breadth.negative,
                        color: red
                    }
                ],
                timestamps,
                breadth.unit
            ),
            `${formatWatchMarketCompact(lastValue(breadth.positive))} مثبت`
        ),
        createWatchMarketChartCard(
            "ارزش لحظه‌ای سفارش‌ها و صف‌ها",
            "نمای فعلی پنج ردیف اول سفارش و صف‌های خرید و فروش",
            null,
            renderWatchMarketBars(
                orderSnapshot.labels,
                orderSnapshot.values,
                orderSnapshot.unit,
                [red, green, "#f97316", cyan]
            ),
            null
        ),
        createWatchMarketChartCard(
            "هیجان بازار",
            "شاخص محاسبه‌شده از برتری تعداد نمادهای مثبت یا منفی؛ بازه ‎−۱۰۰ تا ‎+۱۰۰",
            [{ name: "هیجان بازار", color: violet }],
            renderWatchMarketSeries(
                [
                    {
                        name: "هیجان بازار",
                        values: excitement.values,
                        color: violet
                    }
                ],
                timestamps,
                excitement.unit
            ),
            latestExcitement === null || latestExcitement === undefined
                ? "—"
                : `${watchMarketSignedFormatter.format(latestExcitement)}٪`
        )
    ].join("");
    empty.hidden = true;
    container.hidden = false;
    updateWatchMarketStatus();
}

function setWatchMarketLoading(isLoading, showInitialState = false) {
    const button = document.getElementById("refresh-watch-market");
    const loading = document.getElementById("watch-market-loading");
    if (button) {
        button.disabled = isLoading;
        button.classList.toggle("is-refreshing", isLoading);
        button.setAttribute("aria-busy", isLoading ? "true" : "false");
    }
    if (loading) {
        loading.hidden = !(isLoading && showInitialState);
    }
}

async function loadWatchMarket({ forceRefresh = false } = {}) {
    if (watchMarketLoading || (watchMarketLoaded && !forceRefresh)) return;

    watchMarketLoading = true;
    setWatchMarketLoading(true, !watchMarketLoaded);
    try {
        const parameters = new URLSearchParams({ _ts: Date.now().toString() });
        if (forceRefresh) parameters.set("refresh", "1");
        const response = await fetch(`/watch-market?${parameters.toString()}`, {
            cache: "no-store"
        });
        const payload = await response.json();
        if (!response.ok || !payload || typeof payload !== "object") {
            throw new Error("دریافت اطلاعات بازارها ناموفق بود.");
        }

        watchMarketData = payload;
        watchMarketLoaded = true;
        renderWatchMarketCharts();
        if (stockTradeValueInUsd) {
            renderStockTable();
        }
        if (stockWatchlistTradeValueInUsd) {
            renderStockWatchlistTable();
        }
    } catch (error) {
        console.error("Watch market error:", error);
        const status = document.getElementById("watch-market-status");
        if (status) status.textContent = "دریافت اطلاعات بازارها ناموفق بود.";
        if (!watchMarketLoaded) {
            const empty = document.getElementById("watch-market-empty");
            if (empty) empty.hidden = false;
        }
    } finally {
        watchMarketLoading = false;
        setWatchMarketLoading(false);
    }
}

function startWatchMarketAutoRefresh() {
    window.clearInterval(watchMarketAutoRefreshTimer);
    watchMarketAutoRefreshTimer = window.setInterval(() => {
        loadWatchMarket({ forceRefresh: true });
    }, DASHBOARD_AUTO_REFRESH_INTERVAL);
}

const APP_TAB_ORDER = ["stocks-tab", "options-tab", "watch-tab"];
let activeAppTabId = null;
let heroImageTransitionToken = 0;
let heroImageCleanupTimer = null;

function normalizeHeroImageSource(source) {
    try {
        return new URL(source, document.baseURI).href;
    } catch (_error) {
        return source || "";
    }
}

function transitionHeroImage({ source, alt, tabId }) {
    const hero = document.querySelector(".expectations-hero");
    const layers = hero
        ? [...hero.querySelectorAll(".hero-image-layer")]
        : [];

    if (!hero || layers.length < 2 || !source) return;

    const current = hero.querySelector(".hero-image-layer.is-visible") || layers[0];
    const incoming = layers.find(layer => layer !== current);
    const previousTabIndex = APP_TAB_ORDER.indexOf(activeAppTabId);
    const nextTabIndex = APP_TAB_ORDER.indexOf(tabId);
    const transitionToken = ++heroImageTransitionToken;

    activeAppTabId = tabId;

    if (
        normalizeHeroImageSource(current.getAttribute("src"))
        === normalizeHeroImageSource(source)
    ) {
        current.alt = alt;
        current.removeAttribute("aria-hidden");
        return;
    }

    window.clearTimeout(heroImageCleanupTimer);
    hero.dataset.transitionDirection =
        previousTabIndex >= 0 && nextTabIndex < previousTabIndex
            ? "backward"
            : "forward";
    hero.classList.remove("is-switching");

    layers.forEach(layer => {
        if (layer !== current) {
            layer.classList.remove("is-visible", "is-leaving");
            layer.alt = "";
            layer.setAttribute("aria-hidden", "true");
        }
    });

    incoming.src = source;

    const revealIncomingImage = () => {
        if (transitionToken !== heroImageTransitionToken) return;

        requestAnimationFrame(() => {
            if (transitionToken !== heroImageTransitionToken) return;

            current.classList.remove("is-visible");
            current.classList.add("is-leaving");
            current.alt = "";
            current.setAttribute("aria-hidden", "true");

            incoming.classList.add("is-visible");
            incoming.alt = alt;
            incoming.removeAttribute("aria-hidden");
            hero.classList.add("is-switching");

            heroImageCleanupTimer = window.setTimeout(() => {
                if (transitionToken !== heroImageTransitionToken) return;
                current.classList.remove("is-leaving");
                hero.classList.remove("is-switching");
            }, 740);
        });
    };

    if (incoming.complete && incoming.naturalWidth > 0) {
        revealIncomingImage();
    } else {
        incoming.addEventListener("load", revealIncomingImage, { once: true });
    }
}

function setActiveAppTab(tabId) {
    const isStocksTab = tabId === "stocks-tab";
    const isStockWatchlistTab = tabId === "watchlist-tab";
    const isStrategyTab = tabId === "strategy-tab";
    const isOptionsTab = tabId === "options-tab";
    const isWatchTab = tabId === "watch-tab";

    document.querySelectorAll("[data-app-tab]").forEach(button => {
        const isActive = button.dataset.appTab === tabId;
        button.classList.toggle("active", isActive);
        button.setAttribute("aria-selected", String(isActive));

        if (isActive) {
            button.setAttribute("aria-current", "page");
        } else {
            button.removeAttribute("aria-current");
        }
    });

    document.querySelectorAll(".app-main > .tab-content").forEach(panel => {
        panel.classList.toggle("active", panel.id === tabId);
    });

    const hero = document.querySelector(".expectations-hero");
    const heroImage = document.getElementById("page-hero-image");
    const pageTitle = document.getElementById("page-title");

    if (hero) {
        hero.hidden = false;
    }

    if (heroImage) {
        const nextHeroSource = isStocksTab || isStockWatchlistTab || isStrategyTab
            ? heroImage.dataset.stocksSrc
            : isOptionsTab
                ? heroImage.dataset.optionsSrc
                : heroImage.dataset.marketsSrc;
        const nextHeroAlt = isStocksTab || isStockWatchlistTab || isStrategyTab
            ? "تصویر تحلیلی بازار سهام"
            : isOptionsTab
                ? "تصویر تحلیلی بازار آپشن"
                : "تصویر تحلیلی بازارهای مالی";

        transitionHeroImage({
            source: nextHeroSource,
            alt: nextHeroAlt,
            tabId
        });
    }

    if (pageTitle) {
        pageTitle.textContent = isStocksTab
            ? "دیدبان بازار سهام"
            : isStockWatchlistTab
                ? "دیده‌بان نمادها"
            : isStrategyTab
                ? "استراتژی سهام"
            : isOptionsTab
                ? "تحلیل بازار آپشن"
                : "بازارها";
    }

    if (isStocksTab) {
        setStockWatchlistColumnMenu(false);
        loadStockCatalog();
    } else if (isStockWatchlistTab) {
        setStockColumnMenu(false);
        loadStockWatchlist();
    } else if (isStrategyTab) {
        setStockColumnMenu(false);
        setStockWatchlistColumnMenu(false);
        loadStockStrategy();
    } else if (isWatchTab) {
        setStockColumnMenu(false);
        setStockWatchlistColumnMenu(false);
        loadWatchMarket();
    } else {
        setStockColumnMenu(false);
        setStockWatchlistColumnMenu(false);
    }
}

function initializeAppTabs() {
    document.querySelectorAll("[data-app-tab]").forEach(button => {
        button.addEventListener("click", () => {
            setActiveAppTab(button.dataset.appTab);
            const hash = {
                "stocks-tab": "#stocks",
                "watchlist-tab": "#watchlist",
                "strategy-tab": "#strategy",
                "options-tab": "#options",
                "watch-tab": "#markets"
            }[button.dataset.appTab] || "#stocks";
            history.replaceState(null, "", hash);
        });
    });

    const initialTab = {
        "#options": "options-tab",
        "#watchlist": "watchlist-tab",
        "#strategy": "strategy-tab",
        "#watch": "watch-tab",
        "#markets": "watch-tab",
        "#stocks": "stocks-tab"
    }[window.location.hash] || "stocks-tab";
    setActiveAppTab(initialTab);
}

function loadStockColumnPreferences() {
    try {
        const saved = JSON.parse(
            localStorage.getItem("stock-dashboard-hidden-columns") || "[]"
        );
        const validKeys = new Set(stockTableColumns.map(column => column.key));

        if (Array.isArray(saved)) {
            saved.forEach(key => {
                if (validKeys.has(key)) hiddenStockColumns.add(key);
            });
        }
    } catch (error) {
        console.warn("Could not restore stock column preferences.", error);
    }
}

function saveStockColumnPreferences() {
    try {
        localStorage.setItem(
            "stock-dashboard-hidden-columns",
            JSON.stringify([...hiddenStockColumns])
        );
    } catch (error) {
        console.warn("Could not save stock column preferences.", error);
    }
}

function setStockColumnMenu(open) {
    const selector = document.getElementById("stock-column-selector");
    const toggle = document.getElementById("stock-column-toggle");
    const menu = document.getElementById("stock-column-menu");
    if (!selector || !toggle || !menu) return;

    selector.classList.toggle("open", open);
    toggle.setAttribute("aria-expanded", String(open));
    menu.hidden = !open;
}

function renderStockColumnControls() {
    const container = document.getElementById("stock-column-options");
    if (!container) return;

    const fragment = document.createDocumentFragment();

    stockTableColumns.forEach(column => {
        const label = document.createElement("label");
        label.className = "stock-column-option";

        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.value = column.key;
        checkbox.checked = !hiddenStockColumns.has(column.key);

        const text = document.createElement("span");
        text.textContent = column.side
            ? `${column.label} — ${column.side}`
            : column.label;

        checkbox.addEventListener("change", () => {
            if (checkbox.checked) {
                hiddenStockColumns.delete(column.key);
            } else {
                hiddenStockColumns.add(column.key);
            }

            saveStockColumnPreferences();
            renderStockTable();
        });

        label.append(checkbox, text);
        fragment.appendChild(label);
    });

    container.replaceChildren(fragment);
}

function initializeStockColumnSelector() {
    loadStockColumnPreferences();
    renderStockColumnControls();

    document.getElementById("stock-column-toggle")?.addEventListener(
        "click",
        event => {
            event.stopPropagation();
            const isOpen = event.currentTarget.getAttribute("aria-expanded") === "true";
            setStockColumnMenu(!isOpen);
        }
    );

    document.getElementById("stock-column-menu")?.addEventListener(
        "click",
        event => event.stopPropagation()
    );

    document.getElementById("show-all-stock-columns")?.addEventListener(
        "click",
        () => {
            hiddenStockColumns.clear();
            saveStockColumnPreferences();
            renderStockColumnControls();
            renderStockTable();
        }
    );

    document.addEventListener("click", event => {
        if (!event.target.closest("#stock-column-selector")) {
            setStockColumnMenu(false);
        }
    });
}

function loadStockWatchlistColumnPreferences() {
    try {
        const saved = JSON.parse(
            localStorage.getItem("stock-watchlist-hidden-columns") || "[]"
        );
        const validKeys = new Set(stockTableColumns.map(column => column.key));
        if (Array.isArray(saved)) {
            saved.forEach(key => {
                if (validKeys.has(key)) hiddenStockWatchlistColumns.add(key);
            });
        }
    } catch (error) {
        console.warn("Could not restore watchlist column preferences.", error);
    }
}

function saveStockWatchlistColumnPreferences() {
    try {
        localStorage.setItem(
            "stock-watchlist-hidden-columns",
            JSON.stringify([...hiddenStockWatchlistColumns])
        );
    } catch (error) {
        console.warn("Could not save watchlist column preferences.", error);
    }
}

function setStockWatchlistColumnMenu(open) {
    const selector = document.getElementById("watchlist-column-selector");
    const toggle = document.getElementById("watchlist-column-toggle");
    const menu = document.getElementById("watchlist-column-menu");
    if (!selector || !toggle || !menu) return;

    selector.classList.toggle("open", open);
    toggle.setAttribute("aria-expanded", String(open));
    menu.hidden = !open;
}

function renderStockWatchlistColumnControls() {
    const container = document.getElementById("watchlist-column-options");
    if (!container) return;

    const fragment = document.createDocumentFragment();
    stockTableColumns.forEach(column => {
        const label = document.createElement("label");
        label.className = "stock-column-option";

        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.value = column.key;
        checkbox.checked = column.key === "symbol"
            || !hiddenStockWatchlistColumns.has(column.key);
        checkbox.disabled = column.key === "symbol";

        const text = document.createElement("span");
        text.textContent = column.side
            ? `${column.label} — ${column.side}`
            : column.label;

        checkbox.addEventListener("change", () => {
            if (checkbox.checked) {
                hiddenStockWatchlistColumns.delete(column.key);
            } else {
                hiddenStockWatchlistColumns.add(column.key);
            }
            saveStockWatchlistColumnPreferences();
            renderStockWatchlistTable();
        });

        label.append(checkbox, text);
        fragment.appendChild(label);
    });
    container.replaceChildren(fragment);
}

function initializeStockWatchlistColumnSelector() {
    loadStockWatchlistColumnPreferences();
    renderStockWatchlistColumnControls();

    document.getElementById("watchlist-column-toggle")?.addEventListener(
        "click",
        event => {
            event.stopPropagation();
            const isOpen = event.currentTarget.getAttribute("aria-expanded") === "true";
            setStockWatchlistColumnMenu(!isOpen);
        }
    );
    document.getElementById("watchlist-column-menu")?.addEventListener(
        "click",
        event => event.stopPropagation()
    );
    document.getElementById("show-all-watchlist-columns")?.addEventListener(
        "click",
        () => {
            hiddenStockWatchlistColumns.clear();
            saveStockWatchlistColumnPreferences();
            renderStockWatchlistColumnControls();
            renderStockWatchlistTable();
        }
    );
    document.addEventListener("click", event => {
        if (!event.target.closest("#watchlist-column-selector")) {
            setStockWatchlistColumnMenu(false);
        }
    });
}

function setStockTradeValueCurrency(useDollar) {
    stockTradeValueInUsd = Boolean(useDollar);
    renderStockTable();
}

function isStockInWatchlist(symbol) {
    const target = normalizeSymbol(symbol);
    return stockWatchlistRows.some(
        row => normalizeSymbol(row?.symbol) === target
    );
}

function setStockWatchlistAddButtonState(button, isAdded) {
    if (!button) return;
    const symbol = button.dataset.watchlistAddSymbol || "";
    button.disabled = isAdded;
    button.classList.toggle("is-added", isAdded);
    button.title = isAdded
        ? `${symbol} در دیده‌بان وجود دارد`
        : `افزودن ${symbol} به دیده‌بان`;
    button.setAttribute(
        "aria-label",
        isAdded
            ? `نماد ${symbol} در دیده‌بان وجود دارد`
            : `افزودن نماد ${symbol} به دیده‌بان`
    );
    button.innerHTML = isAdded
        ? `
            <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <path d="m5 12.5 4.2 4.2L19 7"></path>
            </svg>
        `
        : `
            <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <path d="M12 5v14M5 12h14"></path>
            </svg>
        `;
}

function updateStockWatchlistAddButtons() {
    document.querySelectorAll("[data-watchlist-add-symbol]").forEach(button => {
        setStockWatchlistAddButtonState(
            button,
            isStockInWatchlist(button.dataset.watchlistAddSymbol)
        );
    });
}

function createStockWatchlistAddButton(symbol) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "stocks-watchlist-add-button";
    button.dataset.watchlistAddSymbol = symbol || "";
    setStockWatchlistAddButtonState(button, isStockInWatchlist(symbol));
    button.addEventListener("pointerdown", event => event.stopPropagation());
    button.addEventListener("click", event => {
        event.stopPropagation();
        if (button.disabled) return;
        addStockWatchlistSymbol(symbol, button);
    });
    return button;
}

function initializeStockViewControls() {
    document.getElementById("stock-refresh-button")?.addEventListener(
        "click",
        () => requestStockCatalog({ forceRefresh: true })
    );

    document.getElementById("stock-search")?.addEventListener(
        "input",
        event => {
            stockSearchQuery = normalizeSymbol(
                event.target.value
            ).toLocaleLowerCase("fa");
            renderStockTable();
        }
    );

    document.getElementById("stock-industry-search")?.addEventListener(
        "input",
        event => {
            stockIndustryQuery = normalizeSymbol(
                event.target.value
            ).toLocaleLowerCase("fa");
            renderStockTable();
            renderStockIndustryOptions();
            setStockIndustrySuggestionMenu(true);
        }
    );

    document.getElementById("stock-industry-search")?.addEventListener(
        "focus",
        () => {
            renderStockIndustryOptions();
            setStockIndustrySuggestionMenu(true);
        }
    );

    document.getElementById("stock-industry-search")?.addEventListener(
        "keydown",
        event => {
            if (event.key === "Escape") {
                setStockIndustrySuggestionMenu(false);
                event.currentTarget.blur();
            } else if (event.key === "ArrowDown") {
                const firstOption = document.querySelector(
                    "#stock-industry-suggestions button"
                );
                if (firstOption) {
                    event.preventDefault();
                    firstOption.focus();
                }
            }
        }
    );

    document.addEventListener("click", event => {
        if (!event.target.closest(".stock-industry-search")) {
            setStockIndustrySuggestionMenu(false);
        }
    });

    document.getElementById("stock-group-by-industry")?.addEventListener(
        "change",
        event => {
            stockGroupByIndustry = event.target.checked;
            renderStockTable();
        }
    );

    document.getElementById("stock-trade-value-usd")?.addEventListener(
        "change",
        event => setStockTradeValueCurrency(event.target.checked)
    );

    const applyFilter = () => {
        const minInput = document.getElementById("stock-market-min");
        const maxInput = document.getElementById("stock-market-max");
        if (!minInput || !maxInput) return;

        minInput.setCustomValidity("");
        maxInput.setCustomValidity("");

        const minValue = minInput.value === "" ? null : Number(minInput.value);
        const maxValue = maxInput.value === "" ? null : Number(maxInput.value);

        if (minValue !== null && (!Number.isFinite(minValue) || minValue < 0)) {
            minInput.setCustomValidity("حداقل ارزش بازار باید یک عدد مثبت باشد.");
            minInput.reportValidity();
            return;
        }

        if (maxValue !== null && (!Number.isFinite(maxValue) || maxValue < 0)) {
            maxInput.setCustomValidity("حداکثر ارزش بازار باید یک عدد مثبت باشد.");
            maxInput.reportValidity();
            return;
        }

        if (minValue !== null && maxValue !== null && minValue > maxValue) {
            maxInput.setCustomValidity("حداکثر ارزش بازار باید از حداقل بزرگ‌تر باشد.");
            maxInput.reportValidity();
            return;
        }

        stockMarketFilter = { min: minValue, max: maxValue };
        renderStockTable();
    };

    document.getElementById("apply-stock-filter")?.addEventListener(
        "click",
        applyFilter
    );

    document.getElementById("clear-stock-filter")?.addEventListener(
        "click",
        () => {
            const minInput = document.getElementById("stock-market-min");
            const maxInput = document.getElementById("stock-market-max");
            if (minInput) {
                minInput.value = "";
                minInput.setCustomValidity("");
            }
            if (maxInput) {
                maxInput.value = "";
                maxInput.setCustomValidity("");
            }
            const searchInput = document.getElementById("stock-search");
            if (searchInput) searchInput.value = "";
            const industryInput = document.getElementById("stock-industry-search");
            if (industryInput) industryInput.value = "";
            stockSearchQuery = "";
            stockIndustryQuery = "";
            stockMarketFilter = { min: null, max: null };
            setStockIndustrySuggestionMenu(false);
            renderStockTable();
        }
    );

    ["stock-market-min", "stock-market-max"].forEach(inputId => {
        document.getElementById(inputId)?.addEventListener("keydown", event => {
            if (event.key !== "Enter") return;
            event.preventDefault();
            applyFilter();
        });
    });
}

function initializeStockWatchlistControls() {
    document.getElementById("watchlist-add-form")?.addEventListener(
        "submit",
        event => {
            event.preventDefault();
            const input = document.getElementById("watchlist-symbol-input");
            addStockWatchlistSymbol(input?.value || "");
        }
    );

    document.getElementById("watchlist-refresh-button")?.addEventListener(
        "click",
        () => requestStockWatchlist({ forceRefresh: true })
    );

    document.getElementById("watchlist-search")?.addEventListener(
        "input",
        event => {
            stockWatchlistSearchQuery = normalizeSymbol(
                event.target.value
            ).toLocaleLowerCase("fa");
            renderStockWatchlistTable();
        }
    );

    document.getElementById("watchlist-group-by-industry")?.addEventListener(
        "change",
        event => {
            stockWatchlistGroupByIndustry = event.target.checked;
            renderStockWatchlistTable();
        }
    );

    document.getElementById("watchlist-trade-value-usd")?.addEventListener(
        "change",
        event => {
            stockWatchlistTradeValueInUsd = event.target.checked;
            renderStockWatchlistTable();
        }
    );

}

const initializedStockDragWrappers = new WeakSet();

function initializeStockTableDragScroll(wrapperOrId = "stocks-table-wrap") {
    const wrapper = typeof wrapperOrId === "string"
        ? document.getElementById(wrapperOrId)
        : wrapperOrId;
    if (!wrapper || initializedStockDragWrappers.has(wrapper)) return;
    initializedStockDragWrappers.add(wrapper);

    let activePointerId = null;
    let startX = 0;
    let startScrollLeft = 0;
    let dragged = false;
    let suppressClick = false;

    wrapper.addEventListener("pointerdown", event => {
        if (event.button !== 0 || event.pointerType === "touch") return;

        activePointerId = event.pointerId;
        startX = event.clientX;
        startScrollLeft = wrapper.scrollLeft;
        dragged = false;
    });

    wrapper.addEventListener("pointermove", event => {
        if (event.pointerId !== activePointerId) return;

        const deltaX = event.clientX - startX;
        if (!dragged && Math.abs(deltaX) < 5) return;

        if (!dragged) {
            dragged = true;
            wrapper.setPointerCapture?.(event.pointerId);
        }
        wrapper.classList.add("is-dragging");
        event.preventDefault();

        wrapper.scrollLeft = startScrollLeft - deltaX;
    });

    const finishDrag = event => {
        if (event.pointerId !== activePointerId) return;

        if (dragged) {
            suppressClick = true;
            window.setTimeout(() => {
                suppressClick = false;
            }, 0);
        }

        wrapper.classList.remove("is-dragging");
        if (wrapper.hasPointerCapture?.(event.pointerId)) {
            wrapper.releasePointerCapture(event.pointerId);
        }
        activePointerId = null;
        dragged = false;
    };

    window.addEventListener("pointerup", finishDrag);
    window.addEventListener("pointercancel", finishDrag);
    wrapper.addEventListener("dragstart", event => event.preventDefault());
    wrapper.addEventListener(
        "click",
        event => {
            if (!suppressClick) return;
            event.preventDefault();
            event.stopImmediatePropagation();
            suppressClick = false;
        },
        true
    );
}

const frozenStockTableControllers = new WeakMap();

function initializeFrozenStockTable(wrapper, table) {
    if (!wrapper || !table) return;

    const existingController = frozenStockTableControllers.get(wrapper);
    if (existingController) {
        existingController.schedule();
        return;
    }

    let animationFrame = null;
    const sync = () => {
        animationFrame = null;
        const headers = [...table.querySelectorAll("thead th")];
        const pinnedCells = [
            ...table.querySelectorAll(
                "thead th.stocks-pinned-symbol, tbody td.stocks-pinned-symbol"
            )
        ];
        if (!headers.length || !pinnedCells.length) return;

        headers.forEach(header => {
            header.style.transform = "none";
        });
        pinnedCells.forEach(cell => {
            if (!cell.closest("thead")) cell.style.transform = "none";
        });

        const wrapperRect = wrapper.getBoundingClientRect();
        const firstHeaderRect = headers[0].getBoundingClientRect();
        const pinnedRect = pinnedCells[0].getBoundingClientRect();
        const verticalOffset = Math.max(
            0,
            wrapperRect.top + 1 - firstHeaderRect.top
        );
        const horizontalOffset = wrapperRect.right - 1 - pinnedRect.right;

        headers.forEach(header => {
            const x = header.classList.contains("stocks-pinned-symbol")
                ? horizontalOffset
                : 0;
            header.style.transform = `translate3d(${x}px, ${verticalOffset}px, 0)`;
        });
        pinnedCells.forEach(cell => {
            if (cell.closest("thead")) return;
            cell.style.transform = `translate3d(${horizontalOffset}px, 0, 0)`;
        });
    };

    const schedule = () => {
        if (animationFrame !== null) return;
        animationFrame = requestAnimationFrame(sync);
    };

    wrapper.classList.add("has-frozen-pane-js");
    wrapper.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    frozenStockTableControllers.set(wrapper, { schedule });
    schedule();
}

function formatCompactMarketValue(value) {
    const numericValue = Number(value);
    if (!Number.isFinite(numericValue)) return "—";

    const hemmat = numericValue / 10_000_000_000_000;
    return new Intl.NumberFormat("fa-IR", {
        maximumFractionDigits: 0
    }).format(hemmat);
}

function formatTradeValue(value) {
    const numericValue = Number(value);
    if (!Number.isFinite(numericValue)) return "—";

    const billionToman = numericValue / 10_000_000_000;
    return new Intl.NumberFormat("fa-IR", {
        maximumFractionDigits: 2
    }).format(billionToman);
}

function formatStockPerCapita(value) {
    const numericValue = Number(value);
    if (!Number.isFinite(numericValue)) return "—";

    const millionToman = numericValue / 10_000_000;
    return new Intl.NumberFormat("fa-IR", {
        maximumFractionDigits: millionToman >= 100 ? 0 : 2
    }).format(millionToman);
}

function formatStockRatio(value) {
    const numericValue = Number(value);
    if (!Number.isFinite(numericValue)) return "—";
    return new Intl.NumberFormat("fa-IR", {
        maximumFractionDigits: 2
    }).format(numericValue);
}

function getStockDollarRate() {
    const prices = watchMarketData?.overview?.prices;
    if (!Array.isArray(prices)) return null;

    const dollar = prices.find(item => item?.key === "dollar");
    const rate = Number(dollar?.price);
    return Number.isFinite(rate) && rate > 0 ? rate : null;
}

function convertStockTradeValueToDollar(value) {
    const rialValue = Number(value);
    const dollarTomanRate = getStockDollarRate();
    if (!Number.isFinite(rialValue) || !dollarTomanRate) return null;
    return rialValue / 10 / dollarTomanRate;
}

function formatDollarTradeValue(value) {
    const dollarValue = convertStockTradeValueToDollar(value);
    if (!Number.isFinite(dollarValue)) return "—";

    const thousandDollar = dollarValue / 1_000;
    const absoluteValue = Math.abs(thousandDollar);
    const maximumFractionDigits = absoluteValue >= 100
        ? 0
        : absoluteValue >= 10
            ? 1
            : 2;
    return new Intl.NumberFormat("fa-IR", {
        maximumFractionDigits
    }).format(thousandDollar);
}

function getStockColumnUnit(column, useDollar = stockTradeValueInUsd) {
    if (dollarConvertibleStockColumns.has(column.key) && useDollar) {
        return "هزار دلار";
    }
    return column.unit;
}

function formatStockInteger(value) {
    const numericValue = Number(value);
    if (!Number.isFinite(numericValue)) return "—";

    return new Intl.NumberFormat("fa-IR", {
        maximumFractionDigits: 0
    }).format(numericValue);
}

function formatStockChangePercent(value) {
    if (value === null || value === undefined || value === "") return "—";

    const numericValue = Number(value);
    if (!Number.isFinite(numericValue)) return "—";

    return `${new Intl.NumberFormat("fa-IR", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
        signDisplay: "exceptZero"
    }).format(numericValue)}٪`;
}

function formatScaledStockNumber(value, divisor) {
    const numericValue = Number(value);
    if (!Number.isFinite(numericValue)) return "—";

    const scaledValue = numericValue / divisor;
    const scaledAbsoluteValue = Math.abs(scaledValue);
    const maximumFractionDigits = scaledAbsoluteValue >= 10 ? 1 : 2;

    return `${new Intl.NumberFormat("fa-IR", {
        maximumFractionDigits
    }).format(scaledValue)}`;
}

function formatStockCell(column, value, useDollar = stockTradeValueInUsd) {
    if (value === null || value === undefined || value === "") return "—";

    if (column.format === "marketValue") {
        return formatCompactMarketValue(value);
    }
    if (dollarConvertibleStockColumns.has(column.key) && useDollar) {
        return formatDollarTradeValue(value);
    }
    if (column.format === "tradeValue") {
        return formatTradeValue(value);
    }
    if (column.format === "percent") {
        const numericValue = Number(value);
        if (!Number.isFinite(numericValue)) return "—";
        return `${new Intl.NumberFormat("fa-IR", {
            maximumFractionDigits: 2
        }).format(numericValue)}٪`;
    }
    if (column.format === "precisePercent") {
        const numericValue = Number(value);
        if (!Number.isFinite(numericValue)) return "—";
        return `${new Intl.NumberFormat("fa-IR", {
            maximumFractionDigits: Math.abs(numericValue) < 0.1 ? 4 : 2
        }).format(numericValue)}٪`;
    }
    if (column.format === "perCapita") {
        return formatStockPerCapita(value);
    }
    if (column.format === "ratio") {
        return formatStockRatio(value);
    }
    if (column.format === "integer") {
        return formatStockInteger(value);
    }
    if (column.format === "price") {
        return formatStockInteger(value);
    }
    if (column.format === "million") {
        return formatScaledStockNumber(value, 1_000_000);
    }
    if (column.format === "billion") {
        return formatScaledStockNumber(value, 1_000_000_000);
    }

    return String(value);
}

function getFilteredStockRows() {
    return stockCatalogRows.filter(stock => {
        if (stockSearchQuery) {
            const searchableValue = [
                stock.symbol,
                stock.company
            ]
                .map(value => normalizeSymbol(value).toLocaleLowerCase("fa"))
                .join("|");

            if (!searchableValue.includes(stockSearchQuery)) return false;
        }

        if (stockIndustryQuery) {
            const industry = normalizeSymbol(
                stock.industry
            ).toLocaleLowerCase("fa");
            if (!industry.includes(stockIndustryQuery)) return false;
        }

        const marketValue = Number(stock.market_value);

        if (stockMarketFilter.min !== null) {
            if (!Number.isFinite(marketValue)) return false;
            if ((marketValue / 10_000_000_000_000) < stockMarketFilter.min) {
                return false;
            }
        }

        if (stockMarketFilter.max !== null) {
            if (!Number.isFinite(marketValue)) return false;
            if ((marketValue / 10_000_000_000_000) > stockMarketFilter.max) {
                return false;
            }
        }

        return true;
    });
}

function updateStockCount(visibleCount) {
    const count = document.getElementById("stocks-count");
    if (!count) return;

    const formatter = new Intl.NumberFormat("fa-IR");
    count.textContent = visibleCount === stockCatalogRows.length
        ? `${formatter.format(stockCatalogRows.length)} نماد`
        : `${formatter.format(visibleCount)} از ${formatter.format(stockCatalogRows.length)} نماد`;
}

function getSortedStockRows(rows) {
    if (!stockTableSort.key || !stockTableSort.direction) {
        return [...rows];
    }

    const column = stockTableColumns.find(
        item => item.key === stockTableSort.key
    );
    if (!column) return [...rows];

    const direction = stockTableSort.direction === "asc" ? 1 : -1;

    return [...rows].sort((left, right) => {
        const leftValue = left[column.key];
        const rightValue = right[column.key];
        const leftMissing = leftValue === null || leftValue === undefined || leftValue === "";
        const rightMissing = rightValue === null || rightValue === undefined || rightValue === "";

        if (leftMissing && rightMissing) return 0;
        if (leftMissing) return 1;
        if (rightMissing) return -1;

        if (column.type === "number") {
            return (Number(leftValue) - Number(rightValue)) * direction;
        }

        return String(leftValue).localeCompare(
            String(rightValue),
            "fa",
            { sensitivity: "base", numeric: true }
        ) * direction;
    });
}

function sortStockTable(columnKey) {
    const column = stockTableColumns.find(item => item.key === columnKey);
    if (!column) return;

    if (!stockSortInteractionStarted || stockTableSort.key !== columnKey) {
        stockTableSort = {
            key: columnKey,
            direction: "asc"
        };
        stockSortInteractionStarted = true;
    } else if (stockTableSort.direction === "asc") {
        stockTableSort.direction = "desc";
    } else {
        stockTableSort = { ...defaultStockTableSort };
        stockSortInteractionStarted = false;
    }

    renderStockTable();
}

function renderStockTable() {
    const table = document.getElementById("stocks-table");
    if (!table) return;

    const tableWrapper = document.getElementById("stocks-table-wrap");
    const syncFrozenPanes = () => initializeFrozenStockTable(
        tableWrapper,
        table
    );
    const tableHead = table.querySelector("thead");
    const tableBody = table.querySelector("tbody");
    const visibleColumns = stockTableColumns.filter(
        column => !hiddenStockColumns.has(column.key)
    );
    const filteredRows = getFilteredStockRows();
    const displayRows = getSortedStockRows(filteredRows);

    updateStockCount(filteredRows.length);

    table.querySelector("colgroup")?.remove();
    const columnGroup = document.createElement("colgroup");
    visibleColumns.forEach(column => {
        const columnElement = document.createElement("col");
        columnElement.style.width = `${column.width || 140}px`;
        columnGroup.appendChild(columnElement);
    });
    table.prepend(columnGroup);
    table.style.minWidth = `${Math.max(
        760,
        visibleColumns.reduce(
            (total, column) => total + (column.width || 140),
            0
        )
    )}px`;

    const headRow = document.createElement("tr");

    visibleColumns.forEach(column => {
        const header = document.createElement("th");
        const isActive = stockTableSort.key === column.key;
        header.dataset.stockColumn = column.key;
        if (column.key === "symbol") {
            header.classList.add("stocks-pinned-symbol");
        }
        if (column.sideKey) header.dataset.stockSide = column.sideKey;
        header.tabIndex = 0;
        header.setAttribute(
            "aria-sort",
            isActive
                ? (stockTableSort.direction === "asc" ? "ascending" : "descending")
                : "none"
        );

        const heading = document.createElement("span");
        heading.className = "stocks-column-heading";

        const label = document.createElement("span");
        label.className = "stocks-column-title";
        label.textContent = column.label;
        heading.appendChild(label);

        const headerDetails = [column.side, getStockColumnUnit(column)].filter(Boolean);
        if (headerDetails.length > 0) {
            const unit = document.createElement("small");
            unit.className = "stocks-column-unit";
            unit.textContent = `(${headerDetails.join(" · ")})`;
            heading.appendChild(unit);
        }

        const indicator = document.createElement("span");
        indicator.className = "stocks-sort-indicator";
        indicator.textContent = isActive
            ? (stockTableSort.direction === "asc" ? "▲" : "▼")
            : "↕";

        header.append(heading, indicator);
        header.addEventListener("click", () => sortStockTable(column.key));
        header.addEventListener("keydown", event => {
            if (event.key !== "Enter" && event.key !== " ") return;
            event.preventDefault();
            sortStockTable(column.key);
        });
        headRow.appendChild(header);
    });

    tableHead.replaceChildren(headRow);

    if (visibleColumns.length === 0) {
        const row = document.createElement("tr");
        const cell = document.createElement("td");
        cell.className = "stocks-no-columns";
        cell.textContent = "هیچ ستونی برای نمایش انتخاب نشده است.";
        row.appendChild(cell);
        tableBody.replaceChildren(row);
        syncFrozenPanes();
        return;
    }

    const rowsFragment = document.createDocumentFragment();

    if (displayRows.length === 0) {
        const row = document.createElement("tr");
        const cell = document.createElement("td");
        cell.className = "stocks-no-columns";
        cell.colSpan = visibleColumns.length;
        cell.textContent = "نمادی مطابق فیلتر انتخاب‌شده پیدا نشد.";
        row.appendChild(cell);
        tableBody.replaceChildren(row);
        syncFrozenPanes();
        return;
    }

    const appendStockRow = (stock, grouped = false) => {
        const row = document.createElement("tr");
        if (grouped) row.classList.add("stock-industry-member");

        visibleColumns.forEach(column => {
            const cell = document.createElement("td");
            cell.dataset.column = column.key;
            if (column.key === "symbol") {
                cell.classList.add("stocks-pinned-symbol");
            }
            if (column.sideKey) cell.dataset.stockSide = column.sideKey;

            if (column.type === "number") {
                cell.classList.add("stocks-numeric-value");
                cell.textContent = formatStockCell(column, stock[column.key]);

                if (stock[column.key] !== null && stock[column.key] !== undefined) {
                    cell.title = new Intl.NumberFormat("fa-IR", {
                        maximumFractionDigits: 2
                    }).format(stock[column.key]);
                }
            } else {
                cell.textContent = formatStockCell(column, stock[column.key]);
            }

            if (column.key === "market_value") {
                cell.className = "stocks-market-value";

                if (Number.isFinite(Number(stock[column.key]))) {
                    cell.title = `${new Intl.NumberFormat("fa-IR").format(stock[column.key])} ریال`;
                }
            } else if ([
                "trade_value",
                "real_money_flow",
                "real_buy_per_capita",
                "real_sell_per_capita",
                "order_book_value",
                "order_book_buy_value",
                "order_book_sell_value"
            ].includes(column.key)) {
                if (Number.isFinite(Number(stock[column.key]))) {
                    if (
                        dollarConvertibleStockColumns.has(column.key)
                        && stockTradeValueInUsd
                    ) {
                        const dollarValue = convertStockTradeValueToDollar(
                            stock[column.key]
                        );
                        const dollarRate = getStockDollarRate();
                        cell.title = Number.isFinite(dollarValue) && dollarRate
                            ? `${new Intl.NumberFormat("fa-IR", { maximumFractionDigits: 0 }).format(dollarValue)} دلار · نرخ ${new Intl.NumberFormat("fa-IR").format(dollarRate)} تومان`
                            : "نرخ دلار آمریکا در دسترس نیست";
                    } else {
                        cell.title = `${new Intl.NumberFormat("fa-IR").format(stock[column.key])} ریال`;
                    }
                }
            }

            if (column.key === "real_money_flow") {
                const flowValue = Number(stock[column.key]);
                if (Number.isFinite(flowValue)) {
                    cell.classList.add(
                        flowValue > 0
                            ? "is-positive"
                            : (flowValue < 0 ? "is-negative" : "is-neutral")
                    );
                }
            }

            if (column.percentKey) {
                const priceStack = document.createElement("span");
                priceStack.className = "stocks-price-stack";

                const priceValue = document.createElement("span");
                priceValue.className = "stocks-price-main";
                priceValue.textContent = formatStockInteger(stock[column.key]);

                const percentValue = stock[column.percentKey];
                const numericPercent = (
                    percentValue === null
                    || percentValue === undefined
                    || percentValue === ""
                ) ? null : Number(percentValue);
                const percent = document.createElement("small");
                percent.className = "stocks-price-change";
                percent.textContent = formatStockChangePercent(percentValue);
                if (Number.isFinite(numericPercent)) {
                    percent.classList.add(
                        numericPercent > 0
                            ? "is-positive"
                            : (numericPercent < 0 ? "is-negative" : "is-neutral")
                    );
                }

                priceStack.append(priceValue, percent);
                cell.replaceChildren(priceStack);
                if (stock[column.key] !== null && stock[column.key] !== undefined) {
                    cell.title = `${new Intl.NumberFormat("fa-IR").format(stock[column.key])} ریال · ${formatStockChangePercent(percentValue)}`;
                }
            }

            if (column.key === "symbol") {
                const symbolContent = document.createElement("span");
                symbolContent.className = "stocks-symbol-content";

                const symbolText = document.createElement("span");
                symbolText.className = "stocks-symbol-name";
                symbolText.textContent = stock.symbol || "—";
                symbolContent.appendChild(symbolText);

                const symbolActions = document.createElement("span");
                symbolActions.className = "stocks-symbol-actions";

                if (stock.ins_code) {
                    const symbolLink = document.createElement("a");
                    symbolLink.className = "stocks-symbol-link";
                    symbolLink.href = `https://www.tsetmc.com/instInfo/${encodeURIComponent(stock.ins_code)}`;
                    symbolLink.target = "_blank";
                    symbolLink.rel = "noopener noreferrer";
                    symbolLink.title = `نمایش ${stock.symbol} در TSETMC`;
                    symbolLink.setAttribute(
                        "aria-label",
                        `نمایش نماد ${stock.symbol} در TSETMC`
                    );
                    symbolLink.addEventListener(
                        "pointerdown",
                        event => event.stopPropagation()
                    );
                    symbolLink.innerHTML = `
                        <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                            <path d="M14 5h5v5"></path>
                            <path d="m19 5-8 8"></path>
                            <path d="M18 13v5a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"></path>
                        </svg>
                    `;
                    symbolActions.appendChild(symbolLink);
                }

                symbolActions.appendChild(
                    createStockWatchlistAddButton(stock.symbol)
                );
                symbolContent.appendChild(symbolActions);

                cell.replaceChildren(symbolContent);
            }

            row.appendChild(cell);
        });

        rowsFragment.appendChild(row);
    };

    if (stockGroupByIndustry) {
        const industryGroups = new Map();

        displayRows.forEach(stock => {
            const industry = stock.industry || "بدون صنعت";
            if (!industryGroups.has(industry)) {
                industryGroups.set(industry, []);
            }
            industryGroups.get(industry).push(stock);
        });

        industryGroups.forEach((stocks, industry) => {
            const groupRow = document.createElement("tr");
            groupRow.className = "stock-industry-group";

            const groupCell = document.createElement("td");
            groupCell.colSpan = visibleColumns.length;

            const groupName = document.createElement("span");
            groupName.className = "stock-industry-group-name";
            groupName.textContent = industry;

            const groupCount = document.createElement("span");
            groupCount.className = "stock-industry-group-count";
            groupCount.textContent = `${new Intl.NumberFormat("fa-IR").format(stocks.length)} نماد`;

            groupCell.append(groupName, groupCount);
            groupRow.appendChild(groupCell);
            rowsFragment.appendChild(groupRow);
            stocks.forEach(stock => appendStockRow(stock, true));
        });
    } else {
        displayRows.forEach(appendStockRow);
    }

    tableBody.replaceChildren(rowsFragment);
    syncFrozenPanes();
}

function getFilteredStockWatchlistRows() {
    return stockWatchlistRows.filter(stock => {
        if (stockWatchlistSearchQuery) {
            const searchableValue = [stock.symbol, stock.company, stock.industry]
                .map(value => normalizeSymbol(value).toLocaleLowerCase("fa"))
                .join("|");
            if (!searchableValue.includes(stockWatchlistSearchQuery)) return false;
        }

        return true;
    });
}

function getSortedStockWatchlistRows(rows) {
    const { key, direction } = stockWatchlistSort;
    if (!key || !direction) return [...rows];
    const column = stockTableColumns.find(item => item.key === key);
    if (!column) return [...rows];
    const order = direction === "asc" ? 1 : -1;

    return [...rows].sort((left, right) => {
        const leftValue = left[key];
        const rightValue = right[key];
        const leftMissing = leftValue === null || leftValue === undefined || leftValue === "";
        const rightMissing = rightValue === null || rightValue === undefined || rightValue === "";
        if (leftMissing && rightMissing) return 0;
        if (leftMissing) return 1;
        if (rightMissing) return -1;
        if (column.type === "number") {
            return (Number(leftValue) - Number(rightValue)) * order;
        }
        return String(leftValue).localeCompare(
            String(rightValue),
            "fa",
            { sensitivity: "base", numeric: true }
        ) * order;
    });
}

function sortStockWatchlistTable(columnKey) {
    if (!stockTableColumns.some(column => column.key === columnKey)) return;
    if (!stockWatchlistSortInteractionStarted || stockWatchlistSort.key !== columnKey) {
        stockWatchlistSort = { key: columnKey, direction: "asc" };
        stockWatchlistSortInteractionStarted = true;
    } else if (stockWatchlistSort.direction === "asc") {
        stockWatchlistSort.direction = "desc";
    } else {
        stockWatchlistSort = { key: null, direction: null };
        stockWatchlistSortInteractionStarted = false;
    }
    renderStockWatchlistTable();
}

function createStockWatchlistCell(stock, column) {
    const cell = document.createElement("td");
    cell.dataset.column = column.key;
    if (column.key === "symbol") cell.classList.add("stocks-pinned-symbol");
    if (column.sideKey) cell.dataset.stockSide = column.sideKey;

    if (column.type === "number") {
        cell.classList.add("stocks-numeric-value");
        cell.textContent = formatStockCell(
            column,
            stock[column.key],
            stockWatchlistTradeValueInUsd
        );
        if (stock[column.key] !== null && stock[column.key] !== undefined) {
            cell.title = new Intl.NumberFormat("fa-IR", {
                maximumFractionDigits: 2
            }).format(stock[column.key]);
        }
    } else {
        cell.textContent = formatStockCell(
            column,
            stock[column.key],
            stockWatchlistTradeValueInUsd
        );
    }

    if (column.key === "market_value") {
        cell.classList.add("stocks-market-value");
        if (Number.isFinite(Number(stock[column.key]))) {
            cell.title = `${new Intl.NumberFormat("fa-IR").format(stock[column.key])} ریال`;
        }
    } else if ([
        "trade_value",
        "real_money_flow",
        "real_buy_per_capita",
        "real_sell_per_capita",
        "order_book_value",
        "order_book_buy_value",
        "order_book_sell_value"
    ].includes(column.key) && Number.isFinite(Number(stock[column.key]))) {
        if (
            dollarConvertibleStockColumns.has(column.key)
            && stockWatchlistTradeValueInUsd
        ) {
            const dollarValue = convertStockTradeValueToDollar(stock[column.key]);
            const dollarRate = getStockDollarRate();
            cell.title = Number.isFinite(dollarValue) && dollarRate
                ? `${new Intl.NumberFormat("fa-IR", { maximumFractionDigits: 0 }).format(dollarValue)} دلار · نرخ ${new Intl.NumberFormat("fa-IR").format(dollarRate)} تومان`
                : "نرخ دلار آمریکا در دسترس نیست";
        } else {
            cell.title = `${new Intl.NumberFormat("fa-IR").format(stock[column.key])} ریال`;
        }
    }

    if (column.key === "real_money_flow") {
        const flowValue = Number(stock[column.key]);
        if (Number.isFinite(flowValue)) {
            cell.classList.add(
                flowValue > 0
                    ? "is-positive"
                    : (flowValue < 0 ? "is-negative" : "is-neutral")
            );
        }
    }

    if (column.percentKey) {
        const priceStack = document.createElement("span");
        priceStack.className = "stocks-price-stack";
        const priceValue = document.createElement("span");
        priceValue.className = "stocks-price-main";
        priceValue.textContent = formatStockInteger(stock[column.key]);
        const percentValue = stock[column.percentKey];
        const numericPercent = (
            percentValue === null || percentValue === undefined || percentValue === ""
        ) ? null : Number(percentValue);
        const percent = document.createElement("small");
        percent.className = "stocks-price-change";
        percent.textContent = formatStockChangePercent(percentValue);
        if (Number.isFinite(numericPercent)) {
            percent.classList.add(
                numericPercent > 0
                    ? "is-positive"
                    : (numericPercent < 0 ? "is-negative" : "is-neutral")
            );
        }
        priceStack.append(priceValue, percent);
        cell.replaceChildren(priceStack);
    }

    if (column.key === "symbol") {
        const symbolContent = document.createElement("span");
        symbolContent.className = "stocks-symbol-content watchlist-symbol-content";

        const symbolText = document.createElement("span");
        symbolText.className = "watchlist-symbol-name";
        symbolText.textContent = stock.symbol || "—";
        symbolContent.appendChild(symbolText);

        const symbolActions = document.createElement("span");
        symbolActions.className = "watchlist-symbol-actions";
        if (stock.ins_code) {
            const symbolLink = document.createElement("a");
            symbolLink.className = "stocks-symbol-link";
            symbolLink.href = `https://www.tsetmc.com/instInfo/${encodeURIComponent(stock.ins_code)}`;
            symbolLink.target = "_blank";
            symbolLink.rel = "noopener noreferrer";
            symbolLink.title = `نمایش ${stock.symbol} در TSETMC`;
            symbolLink.setAttribute("aria-label", `نمایش نماد ${stock.symbol} در TSETMC`);
            symbolLink.addEventListener("pointerdown", event => event.stopPropagation());
            symbolLink.innerHTML = `
                <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                    <path d="M14 5h5v5"></path>
                    <path d="m19 5-8 8"></path>
                    <path d="M18 13v5a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"></path>
                </svg>
            `;
            symbolActions.appendChild(symbolLink);
        }

        const deleteButton = document.createElement("button");
        deleteButton.type = "button";
        deleteButton.className = "watchlist-delete-button";
        deleteButton.title = `حذف ${stock.symbol} از دیده‌بان`;
        deleteButton.setAttribute("aria-label", `حذف نماد ${stock.symbol} از دیده‌بان`);
        deleteButton.innerHTML = `
            <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                <path d="M4 7h16"></path>
                <path d="m9 7 1-2h4l1 2"></path>
                <path d="m6.5 7 .8 12h9.4l.8-12"></path>
                <path d="M10 11v4M14 11v4"></path>
            </svg>
        `;
        deleteButton.addEventListener("pointerdown", event => event.stopPropagation());
        deleteButton.addEventListener("click", event => {
            event.stopPropagation();
            deleteStockWatchlistSymbol(stock.symbol, deleteButton);
        });
        symbolActions.appendChild(deleteButton);
        symbolContent.appendChild(symbolActions);
        cell.replaceChildren(symbolContent);
    }

    return cell;
}

function renderStockWatchlistTable() {
    const table = document.getElementById("watchlist-table");
    if (!table) return;
    const wrapper = document.getElementById("watchlist-table-wrap");
    const tableHead = table.querySelector("thead");
    const tableBody = table.querySelector("tbody");
    const visibleColumns = stockTableColumns.filter(
        column => column.key === "symbol" || !hiddenStockWatchlistColumns.has(column.key)
    );
    const filteredRows = getFilteredStockWatchlistRows();
    const displayRows = getSortedStockWatchlistRows(filteredRows);
    const count = document.getElementById("watchlist-count");
    if (count) {
        const formatter = new Intl.NumberFormat("fa-IR");
        count.textContent = filteredRows.length === stockWatchlistRows.length
            ? `${formatter.format(stockWatchlistRows.length)} نماد`
            : `${formatter.format(filteredRows.length)} از ${formatter.format(stockWatchlistRows.length)} نماد`;
    }

    table.querySelector("colgroup")?.remove();
    const columnGroup = document.createElement("colgroup");
    visibleColumns.forEach(column => {
        const element = document.createElement("col");
        element.style.width = `${column.key === "symbol" ? 190 : (column.width || 140)}px`;
        columnGroup.appendChild(element);
    });
    table.prepend(columnGroup);
    table.style.minWidth = `${Math.max(
        760,
        visibleColumns.reduce(
            (total, column) => total + (column.key === "symbol" ? 190 : (column.width || 140)),
            0
        )
    )}px`;

    const headRow = document.createElement("tr");
    visibleColumns.forEach(column => {
        const header = document.createElement("th");
        const isActive = stockWatchlistSort.key === column.key;
        header.dataset.stockColumn = column.key;
        if (column.key === "symbol") header.classList.add("stocks-pinned-symbol");
        if (column.sideKey) header.dataset.stockSide = column.sideKey;
        header.tabIndex = 0;
        header.setAttribute(
            "aria-sort",
            isActive
                ? (stockWatchlistSort.direction === "asc" ? "ascending" : "descending")
                : "none"
        );
        const heading = document.createElement("span");
        heading.className = "stocks-column-heading";
        const label = document.createElement("span");
        label.className = "stocks-column-title";
        label.textContent = column.label;
        heading.appendChild(label);
        const details = [
            column.side,
            getStockColumnUnit(column, stockWatchlistTradeValueInUsd)
        ].filter(Boolean);
        if (details.length) {
            const unit = document.createElement("small");
            unit.className = "stocks-column-unit";
            unit.textContent = `(${details.join(" · ")})`;
            heading.appendChild(unit);
        }
        const indicator = document.createElement("span");
        indicator.className = "stocks-sort-indicator";
        indicator.textContent = isActive
            ? (stockWatchlistSort.direction === "asc" ? "▲" : "▼")
            : "↕";
        header.append(heading, indicator);
        header.addEventListener("click", () => sortStockWatchlistTable(column.key));
        header.addEventListener("keydown", event => {
            if (event.key !== "Enter" && event.key !== " ") return;
            event.preventDefault();
            sortStockWatchlistTable(column.key);
        });
        headRow.appendChild(header);
    });
    tableHead.replaceChildren(headRow);

    if (!visibleColumns.length || !displayRows.length) {
        const row = document.createElement("tr");
        const cell = document.createElement("td");
        cell.className = "stocks-no-columns";
        cell.colSpan = Math.max(1, visibleColumns.length);
        cell.textContent = visibleColumns.length
            ? "نمادی مطابق فیلتر انتخاب‌شده پیدا نشد."
            : "هیچ ستونی برای نمایش انتخاب نشده است.";
        row.appendChild(cell);
        tableBody.replaceChildren(row);
    } else {
        const fragment = document.createDocumentFragment();
        const appendWatchlistRow = (stock, grouped = false) => {
            const row = document.createElement("tr");
            if (grouped) row.classList.add("stock-industry-member");
            visibleColumns.forEach(column => {
                row.appendChild(createStockWatchlistCell(stock, column));
            });
            fragment.appendChild(row);
        };

        if (stockWatchlistGroupByIndustry) {
            const groups = new Map();
            displayRows.forEach(stock => {
                const industry = stock.industry || "بدون صنعت";
                if (!groups.has(industry)) groups.set(industry, []);
                groups.get(industry).push(stock);
            });
            groups.forEach((stocks, industry) => {
                const groupRow = document.createElement("tr");
                groupRow.className = "stock-industry-group";
                const groupCell = document.createElement("td");
                groupCell.colSpan = visibleColumns.length;

                const groupName = document.createElement("span");
                groupName.className = "stock-industry-group-name";
                groupName.textContent = industry;
                const groupCount = document.createElement("span");
                groupCount.className = "stock-industry-group-count";
                groupCount.textContent = `${new Intl.NumberFormat("fa-IR").format(stocks.length)} نماد`;

                groupCell.append(groupName, groupCount);
                groupRow.appendChild(groupCell);
                fragment.appendChild(groupRow);
                stocks.forEach(stock => appendWatchlistRow(stock, true));
            });
        } else {
            displayRows.forEach(stock => appendWatchlistRow(stock));
        }
        tableBody.replaceChildren(fragment);
    }

    initializeFrozenStockTable(wrapper, table);
}

function setStockIndustrySuggestionMenu(open) {
    const menu = document.getElementById("stock-industry-suggestions");
    const input = document.getElementById("stock-industry-search");
    if (!menu || !input) return;

    menu.hidden = !open;
    input.setAttribute("aria-expanded", String(open));
    document.querySelector(".stock-industry-search")
        ?.classList.toggle("open", open);
}

function selectStockIndustry(industry) {
    const input = document.getElementById("stock-industry-search");
    if (input) input.value = industry;
    stockIndustryQuery = normalizeSymbol(industry).toLocaleLowerCase("fa");
    setStockIndustrySuggestionMenu(false);
    renderStockTable();
}

function renderStockIndustryOptions() {
    const list = document.getElementById("stock-industry-suggestions");
    if (!list) return;

    const industryCounts = new Map();
    stockCatalogRows.forEach(stock => {
        const industry = String(stock.industry || "").trim();
        if (!industry) return;
        industryCounts.set(industry, (industryCounts.get(industry) || 0) + 1);
    });

    const industries = [...industryCounts.keys()]
        .filter(industry => (
            !stockIndustryQuery
            || normalizeSymbol(industry)
                .toLocaleLowerCase("fa")
                .includes(stockIndustryQuery)
        ))
        .sort((left, right) => left.localeCompare(right, "fa"));
    const fragment = document.createDocumentFragment();

    const appendOption = (industry, count, label = industry) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "stock-industry-suggestion";
        button.setAttribute("role", "option");

        const name = document.createElement("span");
        name.className = "stock-industry-suggestion-name";
        name.textContent = label;

        const badge = document.createElement("span");
        badge.className = "stock-industry-suggestion-count";
        badge.textContent = `${new Intl.NumberFormat("fa-IR").format(count)} نماد`;

        button.append(name, badge);
        button.addEventListener("click", () => selectStockIndustry(industry));
        button.addEventListener("keydown", event => {
            if (event.key === "Escape") {
                setStockIndustrySuggestionMenu(false);
                document.getElementById("stock-industry-search")?.focus();
            }
        });
        fragment.appendChild(button);
    };

    if (stockIndustryQuery) {
        appendOption("", stockCatalogRows.length, "همه صنایع");
    }

    industries.forEach(industry => {
        appendOption(industry, industryCounts.get(industry));
    });

    if (industries.length === 0) {
        const empty = document.createElement("div");
        empty.className = "stock-industry-suggestions-empty";
        empty.textContent = "صنعتی مطابق جست‌وجو پیدا نشد.";
        fragment.appendChild(empty);
    }

    list.replaceChildren(fragment);
}

function setStockRefreshButtonState(isRefreshing) {
    const button = document.getElementById("stock-refresh-button");
    if (!button) return;

    button.disabled = Boolean(isRefreshing);
    button.classList.toggle("is-refreshing", Boolean(isRefreshing));
    button.setAttribute("aria-busy", isRefreshing ? "true" : "false");
}

function updateStockSyncStatus(payload) {
    const status = document.getElementById("stocks-sync-status");
    setStockRefreshButtonState(Boolean(payload?.refreshing));
    if (!status) return;

    if (payload?.refreshing) {
        status.textContent = "";
        status.classList.remove("is-refreshing");
        return;
    }

    status.classList.remove("is-refreshing");
    status.textContent = payload?.warning
        ? "نمایش آخرین دادهٔ ذخیره‌شده"
        : "";
}

function applyStockCatalogPayload(payload) {
    const tableWrap = document.getElementById("stocks-table-wrap");
    const empty = document.getElementById("stocks-empty");
    const rows = Array.isArray(payload?.stocks) ? payload.stocks : [];

    stockCatalogRows = rows;
    stockCatalogLoaded = true;
    renderStockIndustryOptions();
    updateStockSyncStatus(payload);

    if (rows.length === 0) {
        if (tableWrap) tableWrap.hidden = true;
        if (empty) empty.hidden = false;
        updateStockCount(0);
        return;
    }

    if (empty) empty.hidden = true;
    renderStockTable();
    if (tableWrap) tableWrap.hidden = false;
}

function scheduleStockRefreshPoll(previousUpdatedAt, attempt = 0) {
    window.clearTimeout(stockRefreshPollTimer);
    if (attempt >= 80) {
        setStockRefreshButtonState(false);
        return;
    }

    stockRefreshPollTimer = window.setTimeout(async () => {
        try {
            const response = await fetch(`/stocks?poll=1&_ts=${Date.now()}`, {
                cache: "no-store"
            });
            const payload = await response.json();
            if (!response.ok) {
                throw new Error(payload.error || "بررسی به‌روزرسانی سهام ناموفق بود.");
            }

            const hasNewData = Boolean(
                payload.source_updated_at
                && payload.source_updated_at !== previousUpdatedAt
            );
            if (hasNewData || !stockCatalogLoaded) {
                applyStockCatalogPayload(payload);
            } else {
                updateStockSyncStatus(payload);
            }

            if (payload.refreshing) {
                scheduleStockRefreshPoll(
                    hasNewData ? payload.source_updated_at : previousUpdatedAt,
                    attempt + 1
                );
            }
        } catch (error) {
            console.error("Stock refresh poll error:", error);
            setStockRefreshButtonState(false);
        }
    }, STOCK_REFRESH_POLL_INTERVAL);
}

async function requestStockCatalog({ forceRefresh = false, initialLoad = false } = {}) {
    if (stockCatalogLoading) return;

    const loading = document.getElementById("stocks-loading");
    const tableWrap = document.getElementById("stocks-table-wrap");
    const empty = document.getElementById("stocks-empty");
    const count = document.getElementById("stocks-count");

    stockCatalogLoading = true;
    if (forceRefresh) {
        setStockRefreshButtonState(true);
    }
    if (initialLoad && !stockCatalogLoaded) {
        if (loading) loading.hidden = false;
        if (tableWrap) tableWrap.hidden = true;
        if (empty) empty.hidden = true;
    }

    try {
        const parameters = new URLSearchParams({ _ts: Date.now().toString() });
        if (forceRefresh) parameters.set("refresh", "1");
        const response = await fetch(`/stocks?${parameters.toString()}`, {
            cache: "no-store"
        });
        const payload = await response.json();

        if (!response.ok) {
            throw new Error(payload.error || "دریافت فهرست سهام ناموفق بود.");
        }

        applyStockCatalogPayload(payload);
        if (payload.refreshing) {
            scheduleStockRefreshPoll(payload.source_updated_at);
        }
    } catch (error) {
        console.error("Stock catalog error:", error);
        setStockRefreshButtonState(false);
        document.getElementById("stocks-sync-status")?.classList.remove("is-refreshing");
        if (!stockCatalogLoaded) {
            if (count) count.textContent = "خطا در دریافت اطلاعات";
            if (empty) {
                empty.textContent = error.message || "دریافت فهرست سهام ناموفق بود.";
                empty.hidden = false;
            }
        }
    } finally {
        stockCatalogLoading = false;
        if (loading) loading.hidden = true;
    }
}

function loadStockCatalog() {
    if (stockCatalogLoaded) return;
    requestStockCatalog({ initialLoad: true });
}

function startStockAutoRefresh() {
    window.clearInterval(stockAutoRefreshTimer);
    stockAutoRefreshTimer = window.setInterval(() => {
        requestStockCatalog({ forceRefresh: true });
    }, STOCK_AUTO_REFRESH_INTERVAL);
}

function setStockWatchlistBusy(isBusy) {
    const refreshButton = document.getElementById("watchlist-refresh-button");
    if (refreshButton) {
        refreshButton.disabled = Boolean(isBusy);
        refreshButton.classList.toggle("is-refreshing", Boolean(isBusy));
        refreshButton.setAttribute("aria-busy", isBusy ? "true" : "false");
    }
}

function setStockWatchlistStatus(message = "", isError = false) {
    const status = document.getElementById("watchlist-status");
    if (!status) return;
    status.textContent = message;
    status.classList.toggle("is-error", Boolean(message && isError));
}

function applyStockWatchlistPayload(payload) {
    const rows = Array.isArray(payload?.stocks) ? payload.stocks : [];
    const tableWrap = document.getElementById("watchlist-table-wrap");
    const empty = document.getElementById("watchlist-empty");
    stockWatchlistRows = rows;
    stockWatchlistLoaded = true;
    setStockWatchlistStatus(payload?.warning || "", Boolean(payload?.warning));
    updateStockWatchlistAddButtons();

    if (!rows.length) {
        if (tableWrap) tableWrap.hidden = true;
        if (empty) {
            empty.textContent = "هنوز نمادی به دیده‌بان اضافه نشده است.";
            empty.hidden = false;
        }
        const count = document.getElementById("watchlist-count");
        if (count) count.textContent = "۰ نماد";
        return;
    }

    if (empty) empty.hidden = true;
    renderStockWatchlistTable();
    if (tableWrap) tableWrap.hidden = false;
}

async function requestStockWatchlist({ forceRefresh = false, initialLoad = false } = {}) {
    if (stockWatchlistLoading) return;
    const loading = document.getElementById("watchlist-loading");
    const tableWrap = document.getElementById("watchlist-table-wrap");
    const empty = document.getElementById("watchlist-empty");

    stockWatchlistLoading = true;
    setStockWatchlistBusy(forceRefresh);
    if (initialLoad && !stockWatchlistLoaded) {
        if (loading) loading.hidden = false;
        if (tableWrap) tableWrap.hidden = true;
        if (empty) empty.hidden = true;
    }

    try {
        const parameters = new URLSearchParams({ _ts: Date.now().toString() });
        if (forceRefresh) parameters.set("refresh", "1");
        const response = await fetch(`/stock-watchlist?${parameters.toString()}`, {
            cache: "no-store"
        });
        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload.error || "دریافت دیده‌بان ناموفق بود.");
        }
        applyStockWatchlistPayload(payload);
    } catch (error) {
        console.error("Stock watchlist error:", error);
        setStockWatchlistStatus(error.message || "دریافت دیده‌بان ناموفق بود.", true);
        if (!stockWatchlistLoaded && empty) {
            empty.textContent = error.message || "دریافت دیده‌بان ناموفق بود.";
            empty.hidden = false;
        }
    } finally {
        stockWatchlistLoading = false;
        setStockWatchlistBusy(false);
        if (loading) loading.hidden = true;
    }
}

async function addStockWatchlistSymbol(rawSymbol, triggerButton = null) {
    const input = document.getElementById("watchlist-symbol-input");
    const formButton = document.getElementById("watchlist-add-button");
    const activeButton = triggerButton || formButton;
    const symbol = normalizeSymbol(rawSymbol);
    if (!symbol) {
        input?.setCustomValidity("نام نماد را وارد کنید.");
        input?.reportValidity();
        return;
    }

    input?.setCustomValidity("");
    if (activeButton) {
        activeButton.disabled = true;
        activeButton.setAttribute("aria-busy", "true");
    }
    setStockWatchlistStatus("");

    try {
        const response = await fetch("/stock-watchlist", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ symbol }),
            cache: "no-store"
        });
        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload.error || "افزودن نماد ناموفق بود.");
        }
        applyStockWatchlistPayload(payload);
        if (input && !triggerButton) {
            input.value = "";
            input.focus();
        }
    } catch (error) {
        console.error("Add stock watchlist symbol error:", error);
        setStockWatchlistStatus(error.message || "افزودن نماد ناموفق بود.", true);
        if (triggerButton) {
            triggerButton.title = error.message || "افزودن نماد ناموفق بود.";
        }
    } finally {
        if (activeButton) {
            activeButton.removeAttribute("aria-busy");
            if (!triggerButton || !isStockInWatchlist(symbol)) {
                activeButton.disabled = false;
            }
        }
    }
}

async function deleteStockWatchlistSymbol(symbol, button) {
    if (!symbol) return;
    if (button) {
        button.disabled = true;
        button.setAttribute("aria-busy", "true");
    }
    setStockWatchlistStatus("");

    try {
        const response = await fetch(
            `/stock-watchlist/${encodeURIComponent(symbol)}`,
            { method: "DELETE", cache: "no-store" }
        );
        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload.error || "حذف نماد ناموفق بود.");
        }
        applyStockWatchlistPayload(payload);
    } catch (error) {
        console.error("Delete stock watchlist symbol error:", error);
        setStockWatchlistStatus(error.message || "حذف نماد ناموفق بود.", true);
        if (button) {
            button.disabled = false;
            button.removeAttribute("aria-busy");
        }
    }
}

function loadStockWatchlist() {
    if (stockWatchlistLoaded) return;
    requestStockWatchlist({ initialLoad: true });
}

function startStockWatchlistAutoRefresh() {
    window.clearInterval(stockWatchlistAutoRefreshTimer);
    stockWatchlistAutoRefreshTimer = window.setInterval(() => {
        requestStockWatchlist({ forceRefresh: true });
    }, DASHBOARD_AUTO_REFRESH_INTERVAL);
}

const stockStrategyControlMap = {
    trade_value: {
        enabled: "strategy-trade-value-enabled",
        operator: "strategy-trade-value-operator",
        days: "strategy-trade-value-days"
    },
    trade_to_float_percent: {
        enabled: "strategy-trade-to-float-enabled",
        operator: "strategy-trade-to-float-operator",
        fixed: "strategy-trade-to-float-fixed",
        days: "strategy-trade-to-float-days"
    },
    real_buy_power: {
        enabled: "strategy-real-buy-power-enabled",
        operator: "strategy-real-buy-power-operator",
        fixed: "strategy-real-buy-power-fixed",
        days: "strategy-real-buy-power-days"
    }
};

function readStockStrategyRules() {
    const rules = {};
    Object.entries(stockStrategyControlMap).forEach(([metric, controls]) => {
        const days = Math.max(
            0,
            Math.min(250, Number(document.getElementById(controls.days)?.value) || 0)
        );
        const fixed = controls.fixed
            ? Math.max(0, Number(document.getElementById(controls.fixed)?.value) || 0)
            : 0;
        rules[metric] = {
            enabled: Boolean(document.getElementById(controls.enabled)?.checked),
            operator: document.getElementById(controls.operator)?.value || "gte",
            days,
            fixed
        };
    });
    return rules;
}

function updateStockStrategyRuleStyles() {
    Object.entries(stockStrategyControlMap).forEach(([metric, controls]) => {
        const enabled = Boolean(document.getElementById(controls.enabled)?.checked);
        document.querySelector(`[data-strategy-rule="${metric}"]`)
            ?.classList.toggle("is-enabled", enabled);
    });
}

function saveStockStrategyRules() {
    try {
        localStorage.setItem(
            "stock-strategy-rules",
            JSON.stringify(readStockStrategyRules())
        );
    } catch (error) {
        console.warn("Could not save stock strategy rules.", error);
    }
}

function restoreStockStrategyRules() {
    try {
        const saved = JSON.parse(localStorage.getItem("stock-strategy-rules") || "null");
        if (!saved || typeof saved !== "object") return;
        Object.entries(stockStrategyControlMap).forEach(([metric, controls]) => {
            const rule = saved[metric];
            if (!rule || typeof rule !== "object") return;
            const enabled = document.getElementById(controls.enabled);
            const operator = document.getElementById(controls.operator);
            const days = document.getElementById(controls.days);
            const fixed = controls.fixed
                ? document.getElementById(controls.fixed)
                : null;
            if (enabled) enabled.checked = Boolean(rule.enabled);
            if (operator && ["gte", "lte", "eq"].includes(rule.operator)) {
                operator.value = rule.operator;
            }
            if (days) days.value = String(Math.max(0, Number(rule.days) || 0));
            if (fixed) fixed.value = String(Math.max(0, Number(rule.fixed) || 0));
        });
    } catch (error) {
        console.warn("Could not restore stock strategy rules.", error);
    }
}

function initializeStockStrategyControls() {
    restoreStockStrategyRules();
    updateStockStrategyRuleStyles();
    document.getElementById("strategy-run-button")?.addEventListener(
        "click",
        () => requestStockStrategy({ showLoading: true })
    );
    document.querySelectorAll(".strategy-rule input, .strategy-rule select")
        .forEach(control => {
            control.addEventListener("change", () => {
                updateStockStrategyRuleStyles();
                saveStockStrategyRules();
            });
            control.addEventListener("keydown", event => {
                if (event.key !== "Enter") return;
                event.preventDefault();
                saveStockStrategyRules();
                requestStockStrategy({ showLoading: true });
            });
        });
}

function formatStockStrategyValue(metric, value) {
    if (value === null || value === undefined || value === "") return "—";
    if (metric === "trade_value") return formatTradeValue(value);
    if (metric === "trade_to_float_percent") {
        return formatStockCell({ key: metric, format: "precisePercent" }, value, false);
    }
    return formatStockRatio(value);
}

function renderStockStrategyTable(payload) {
    const table = document.getElementById("strategy-table");
    const wrapper = document.getElementById("strategy-table-wrap");
    const empty = document.getElementById("strategy-empty");
    const count = document.getElementById("strategy-count");
    const status = document.getElementById("strategy-status");
    if (!table || !wrapper || !empty) return;

    const rows = Array.isArray(payload?.stocks) ? payload.stocks : [];
    const formatter = new Intl.NumberFormat("fa-IR");
    if (count) {
        count.textContent = `${formatter.format(rows.length)} از ${formatter.format(payload?.evaluated_count || 0)} نماد`;
    }
    if (status) {
        status.classList.remove("is-error", "is-warning");
        status.setAttribute("role", "status");
        if (!payload?.active_filter_count) {
            status.textContent = "هیچ شرطی فعال نیست؛ همه نمادها نمایش داده شده‌اند.";
        } else {
            const metricNames = {
                trade_value: "ارزش معاملات",
                trade_to_float_percent: "معامله به شناوری",
                real_buy_power: "قدرت خرید حقیقی"
            };
            const warnings = [];
            Object.entries(payload?.history_coverage || {}).forEach(([metric, coverage]) => {
                if (!coverage?.partial_symbol_count) return;
                const minimum = coverage.minimum_days_used;
                const maximum = coverage.maximum_days_used;
                const usedDays = minimum === maximum
                    ? `${formatter.format(minimum)}روزه`
                    : `${formatter.format(minimum)} تا ${formatter.format(maximum)}روزه`;
                warnings.push(
                    `${metricNames[metric] || metric}: میانگین ${usedDays} به‌جای ${formatter.format(coverage.requested_days)}روزه`
                );
            });
            if (payload?.missing_history_count) {
                warnings.push(
                    `${formatter.format(payload.missing_history_count)} نماد بدون سابقه معتبر حذف شد`
                );
            }
            if (payload?.excluded_zero_or_missing_count) {
                warnings.push(
                    `${formatter.format(payload.excluded_zero_or_missing_count)} نماد با مقدار صفر یا خالی حذف شد`
                );
            }

            if (warnings.length) {
                status.textContent = `هشدار: ${warnings.join("؛ ")}`;
                status.classList.add("is-warning");
                status.setAttribute("role", "alert");
            } else {
                status.textContent = `${formatter.format(payload.active_filter_count)} شرط فعال با منطق «و» اعمال شد.`;
            }
        }
    }

    const columns = [
        { key: "symbol", label: "نماد", width: 150 },
        { key: "company", label: "نام شرکت", width: 210 },
        { key: "industry", label: "صنعت", width: 190 },
        { key: "trade_value", label: "ارزش معاملات امروز", unit: "میلیارد تومان", metric: "trade_value", width: 150 },
        { key: "trade_value_average", label: "میانگین ارزش معاملات", unit: "میلیارد تومان", metric: "trade_value", historyKey: "trade_value_history_count", width: 160 },
        { key: "trade_to_float_percent", label: "معامله به شناوری امروز", unit: "درصد", metric: "trade_to_float_percent", width: 155 },
        { key: "trade_to_float_percent_average", label: "میانگین معامله به شناوری", unit: "درصد", metric: "trade_to_float_percent", historyKey: "trade_to_float_percent_history_count", width: 175 },
        { key: "real_buy_power", label: "قدرت خرید حقیقی امروز", unit: "برابر", metric: "real_buy_power", width: 155 },
        { key: "real_buy_power_average", label: "میانگین قدرت خرید حقیقی", unit: "برابر", metric: "real_buy_power", historyKey: "real_buy_power_history_count", width: 170 }
    ];

    table.querySelector("colgroup")?.remove();
    const colgroup = document.createElement("colgroup");
    columns.forEach(column => {
        const col = document.createElement("col");
        col.style.width = `${column.width}px`;
        colgroup.appendChild(col);
    });
    table.prepend(colgroup);
    table.style.minWidth = `${columns.reduce((total, column) => total + column.width, 0)}px`;

    const headRow = document.createElement("tr");
    columns.forEach(column => {
        const header = document.createElement("th");
        header.dataset.stockColumn = column.key;
        if (column.key === "symbol") header.classList.add("stocks-pinned-symbol");
        const heading = document.createElement("span");
        heading.className = "stocks-column-heading";
        const title = document.createElement("span");
        title.className = "stocks-column-title";
        title.textContent = column.label;
        heading.appendChild(title);
        if (column.unit) {
            const unit = document.createElement("small");
            unit.className = "stocks-column-unit";
            unit.textContent = `(${column.unit})`;
            heading.appendChild(unit);
        }
        header.appendChild(heading);
        headRow.appendChild(header);
    });
    table.querySelector("thead").replaceChildren(headRow);

    if (!rows.length) {
        wrapper.hidden = true;
        empty.textContent = payload?.active_filter_count
            ? "هیچ نمادی تمام شرط‌های فعال را هم‌زمان ندارد."
            : "داده‌ای برای نمایش وجود ندارد.";
        empty.hidden = false;
        return;
    }

    const fragment = document.createDocumentFragment();
    rows.forEach(stock => {
        const row = document.createElement("tr");
        columns.forEach(column => {
            const cell = document.createElement("td");
            cell.dataset.column = column.key;
            if (column.key === "symbol") cell.classList.add("stocks-pinned-symbol");
            if (
                column.historyKey
                && stock[column.key] !== null
                && stock[column.key] !== undefined
            ) {
                const stack = document.createElement("span");
                stack.className = "strategy-comparison-stack";
                const value = document.createElement("span");
                value.textContent = formatStockStrategyValue(
                    column.metric,
                    stock[column.key]
                );
                const days = document.createElement("small");
                days.textContent = `${formatter.format(stock[column.historyKey] || 0)} روزه`;
                stack.append(value, days);
                cell.appendChild(stack);
            } else {
                cell.textContent = column.metric
                    ? formatStockStrategyValue(column.metric, stock[column.key])
                    : (stock[column.key] || "—");
            }
            row.appendChild(cell);
        });
        fragment.appendChild(row);
    });
    table.querySelector("tbody").replaceChildren(fragment);
    empty.hidden = true;
    wrapper.hidden = false;
    initializeStockTableDragScroll(wrapper);
    initializeFrozenStockTable(wrapper, table);
}

async function requestStockStrategy({ showLoading = false } = {}) {
    if (stockStrategyLoading) return;
    const loading = document.getElementById("strategy-loading");
    const button = document.getElementById("strategy-run-button");
    const status = document.getElementById("strategy-status");
    stockStrategyLoading = true;
    if (loading) loading.hidden = !(showLoading && !stockStrategyLoaded);
    if (button) {
        button.disabled = true;
        button.setAttribute("aria-busy", "true");
    }

    try {
        const response = await fetch("/stock-strategy", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ rules: readStockStrategyRules() }),
            cache: "no-store"
        });
        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload.error || "اجرای استراتژی ناموفق بود.");
        }
        stockStrategyLoaded = true;
        renderStockStrategyTable(payload);
    } catch (error) {
        console.error("Stock strategy error:", error);
        if (status) {
            status.textContent = error.message || "اجرای استراتژی ناموفق بود.";
            status.classList.add("is-error");
        }
    } finally {
        stockStrategyLoading = false;
        if (loading) loading.hidden = true;
        if (button) {
            button.disabled = false;
            button.removeAttribute("aria-busy");
        }
    }
}

function loadStockStrategy() {
    if (stockStrategyLoaded) return;
    requestStockStrategy({ showLoading: true });
}

function startStockStrategyAutoRefresh() {
    window.clearInterval(stockStrategyAutoRefreshTimer);
    stockStrategyAutoRefreshTimer = window.setInterval(() => {
        requestStockStrategy();
    }, DASHBOARD_AUTO_REFRESH_INTERVAL);
}

document.addEventListener(
    "DOMContentLoaded",
    async function () {

        initializeStockStrategyControls();
        initializeAppTabs();
        document.getElementById("refresh-watch-market")?.addEventListener(
            "click",
            () => loadWatchMarket({ forceRefresh: true })
        );
        initializeStockColumnSelector();
        initializeStockWatchlistColumnSelector();
        initializeStockViewControls();
        initializeStockWatchlistControls();
        initializeStockTableDragScroll();
        initializeStockTableDragScroll("watchlist-table-wrap");
        loadStockWatchlist();
        startStockAutoRefresh();
        startStockWatchlistAutoRefresh();
        startStockStrategyAutoRefresh();
        startWatchMarketAutoRefresh();

        /*
            رابط دو نمای قدیمی فعلاً حذف شده است، اما تمام توابع دریافت
            و پردازش آن‌ها برای استفاده در مراحل بعدی در همین فایل حفظ می‌شوند.
            اگر آن نماها دوباره به DOM برگردند، راه‌اندازی قبلی نیز فعال می‌شود.
        */
        const legacyViewsAvailable = Boolean(
            document.getElementById("market")
            || document.getElementById("spread")
        );

        if (legacyViewsAvailable) {
            await loadDiscoveredOptionBases();
            populateBaseSymbolDropdown();
            initializeDataSourceDropdown(
                document.getElementById("market-data-source")
            );
            initializeDataSourceDropdown(
                document.getElementById("spread-data-source")
            );
            initializeDataSourceDropdown(
                document.getElementById("filter-status")
            );
            await autoRefreshMarket();
            startAutoRefresh();
        }

        startMarketExpectationsAutoRefresh();

        document
            .getElementById("refresh-expectations")
            ?.addEventListener("click", () => loadMarketExpectations(true));

        document
            .getElementById("nearest-expiry-summary")
            ?.addEventListener("click", openNearestExpirySummary);

        document
            .getElementById("show-expiring-options")
            ?.addEventListener("click", openExpiringOptionsSummary);

        document
            .getElementById("show-market-share-options")
            ?.addEventListener("click", openMarketShareOptionsSummary);

        document
            .getElementById("expectations-market-share-count")
            ?.addEventListener("input", event => {
                event.target.setCustomValidity("");
            });

        document
            .getElementById("expectations-max-days")
            ?.addEventListener("input", event => {
                event.target.setCustomValidity("");
            });

        document
            .getElementById("expectations-min-days")
            ?.addEventListener("input", event => {
                event.target.setCustomValidity("");
                document
                    .getElementById("expectations-max-days")
                    ?.setCustomValidity("");
            });

        document
            .getElementById("expectations-search")
            ?.addEventListener("input", event => {
                filterMarketExpectationSymbols(event.target.value);
            });

        document
            .getElementById("expectations-use-saved-value")
            ?.addEventListener("change", () => {
                loadMarketExpectations(true);
            });

        document
            .getElementById("expectations-list")
            ?.addEventListener("click", event => {
                const button = event.target.closest(".expectations-detail-link");
                if (!button) return;
                openExpectationDetails(
                    Number(button.dataset.baseIndex),
                    button.dataset.groupId
                );
            });

        document
            .querySelectorAll("[data-close-expectations-modal]")
            .forEach(element => element.addEventListener(
                "click", closeExpectationDetails
            ));

        document
            .querySelectorAll("[data-close-nearest-expiry-modal]")
            .forEach(element => element.addEventListener(
                "click", closeNearestExpirySummary
            ));

        document
            .querySelectorAll("[data-close-expiring-options-modal]")
            .forEach(element => element.addEventListener(
                "click", closeExpiringOptionsSummary
            ));

        document
            .querySelectorAll("[data-close-market-share-options-modal]")
            .forEach(element => element.addEventListener(
                "click", closeMarketShareOptionsSummary
            ));

        document
            .querySelector(".nearest-expiry-table tbody")
            ?.addEventListener("click", event => {
                const button = event.target.closest(".nearest-expiry-detail-link");
                if (!button) return;
                openExpectationDetails(
                    Number(button.dataset.baseIndex),
                    button.dataset.groupId
                );
            });

        document
            .querySelector(".expiring-options-table tbody")
            ?.addEventListener("click", event => {
                const button = event.target.closest(".expiring-option-detail-link");
                if (!button) return;
                openExpectationDetails(
                    Number(button.dataset.baseIndex),
                    button.dataset.groupId
                );
            });

        document
            .querySelectorAll(".expectations-summary-table thead")
            .forEach(tableHead => {
                const activateSort = event => {
                    if (event.type === "keydown"
                        && event.key !== "Enter"
                        && event.key !== " ") return;
                    const header = event.target.closest("th[data-sort-type]");
                    if (!header) return;
                    if (event.type === "keydown") event.preventDefault();
                    sortExpectationSummaryTable(
                        header.closest("table"),
                        header
                    );
                };
                tableHead.addEventListener("click", activateSort);
                tableHead.addEventListener("keydown", activateSort);
            });

        document
            .querySelector(".expectations-detail-table thead")
            ?.addEventListener("click", event => {
                const header = event.target.closest("th[data-sort-key]");
                if (header) sortExpectationDetails(header.dataset.sortKey);
            });

        document
            .querySelector(".expectations-detail-table thead")
            ?.addEventListener("keydown", event => {
                if (event.key !== "Enter" && event.key !== " ") return;
                const header = event.target.closest("th[data-sort-key]");
                if (!header) return;
                event.preventDefault();
                sortExpectationDetails(header.dataset.sortKey);
            });

        document.addEventListener("keydown", event => {
            if (event.key === "Escape") {
                const detailModal = document.getElementById("expectations-modal");
                if (detailModal && !detailModal.hidden) {
                    closeExpectationDetails();
                    return;
                }
                closeNearestExpirySummary();
                closeExpiringOptionsSummary();
                closeMarketShareOptionsSummary();
            }
        });

        await loadMarketExpectations();
    }
);

function isTabActive(tabId) {

    return document
        .getElementById(tabId)
        ?.classList.contains("active");
}

async function autoRefreshMarket() {

    // فقط وقتی تب market فعال است
    if (!isTabActive("market")) {
        return;
    }

    if (marketAutoRefreshRunning) {
        return;
    }

    marketAutoRefreshRunning = true;

    try {

        await loadData();

    } catch (error) {

        console.error(
            "Market auto refresh error:",
            error
        );

    } finally {

        marketAutoRefreshRunning = false;
    }
}

async function autoRefreshSpread() {

    // فقط وقتی تب spread فعال است
    if (!isTabActive("spread")) {
        return;
    }

    if (spreadAutoRefreshRunning) {
        return;
    }

    const selectedBaseSymbols =
        getSelectedValues(
            "spread-base-symbol"
        );

    if (selectedBaseSymbols.length === 0) {
        return;
    }

    spreadAutoRefreshRunning = true;
    

    /*
        ردیف انتخاب‌شده را نگه می‌داریم
        تا بعد از Refresh دوباره همان ردیف
        قابل شناسایی باشد.
    */
    const previousSelectedRowKey =
        selectedRowKeys.spreadCalculation;


    try {

        /*
            مرحله اول:
            دریافت مجدد داده‌ها طبق
            تمام فیلترهای فعلی
        */
        const loadSuccess =
            await loadSpreadData(
                true
            );


        if (
            loadSuccess &&
            Array.isArray(spreadOriginalData) &&
            spreadOriginalData.length >= 2
        ) {

            calculateSpreadTable();
        }


        /*
            اگر قبل از Refresh یک ردیف انتخاب
            شده بود، Order Book همان ردیف
            دوباره با داده جدید نمایش داده شود.
        */
        if (
            previousSelectedRowKey &&
            Array.isArray(
                spreadCalculationOriginalData
            ) &&
            spreadCalculationOriginalData.length > 0
        ) {

            const selectedRow =
                spreadCalculationOriginalData.find(
                    (row, index) => {

                        return getTableRowKey(
                            "spreadCalculation",
                            row,
                            index
                        ) === previousSelectedRowKey;
                    }
                );


            if (selectedRow) {

                showSpreadOrderBooks(
                    selectedRow
                );
            }
        }

    } catch (error) {

        console.error(
            "Spread auto refresh error:",
            error
        );

    } finally {

        spreadAutoRefreshRunning = false;
    }
}

function startAutoRefresh() {

    /*
        جلوگیری از ساخته‌شدن Timer تکراری
    */
    if (marketAutoRefreshTimer) {

        clearInterval(
            marketAutoRefreshTimer
        );
    }


    if (spreadAutoRefreshTimer) {

        clearInterval(
            spreadAutoRefreshTimer
        );
    }


    /*
        تب اول
    */
    marketAutoRefreshTimer =
        setInterval(
            autoRefreshMarket,
            AUTO_REFRESH_INTERVAL
        );


    /*
        تب اسپرد
    */
    spreadAutoRefreshTimer =
        setInterval(
            autoRefreshSpread,
            AUTO_REFRESH_INTERVAL
        );

}

function stopAutoRefresh() {

    if (marketAutoRefreshTimer) {

        clearInterval(
            marketAutoRefreshTimer
        );

        marketAutoRefreshTimer = null;
    }


    if (spreadAutoRefreshTimer) {

        clearInterval(
            spreadAutoRefreshTimer
        );

        spreadAutoRefreshTimer = null;
    }

}
