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
        if (isTabActive("expectations")) {
            loadMarketExpectations(true);
        }
    }, 60_000);
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

document.addEventListener(
    "DOMContentLoaded",
    async function () {

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
