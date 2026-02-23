/* ==========================================================================
   Bike Sharing Demand Prediction — Frontend Logic
   ========================================================================== */

(function () {
    "use strict";

    // ---- Mobile nav toggle ------------------------------------------------
    var navToggle = document.getElementById("nav-toggle");
    var navLinks = document.querySelector(".nav-links");
    if (navToggle && navLinks) {
        navToggle.addEventListener("click", function () {
            navLinks.classList.toggle("open");
        });
    }

    // ---- Scroll-triggered animations --------------------------------------
    function initAnimations() {
        var elements = document.querySelectorAll("[data-animate]");
        if (!elements.length) return;

        var observer = new IntersectionObserver(
            function (entries) {
                entries.forEach(function (entry) {
                    if (entry.isIntersecting) {
                        entry.target.classList.add("visible");
                        observer.unobserve(entry.target);
                    }
                });
            },
            { threshold: 0.15 }
        );

        elements.forEach(function (el) {
            observer.observe(el);
        });
    }
    initAnimations();

    // ---- Animated count-up for stat values --------------------------------
    function animateCountUp() {
        var counters = document.querySelectorAll("[data-count]");
        if (!counters.length) return;

        var observer = new IntersectionObserver(
            function (entries) {
                entries.forEach(function (entry) {
                    if (!entry.isIntersecting) return;
                    var el = entry.target;
                    var target = parseInt(el.getAttribute("data-count"), 10);
                    if (isNaN(target)) return;

                    var duration = 1200;
                    var start = 0;
                    var startTime = null;

                    function step(timestamp) {
                        if (!startTime) startTime = timestamp;
                        var progress = Math.min((timestamp - startTime) / duration, 1);
                        // Ease-out cubic
                        var eased = 1 - Math.pow(1 - progress, 3);
                        var current = Math.round(start + (target - start) * eased);
                        el.textContent = current.toLocaleString();
                        if (progress < 1) {
                            requestAnimationFrame(step);
                        }
                    }

                    requestAnimationFrame(step);
                    observer.unobserve(el);
                });
            },
            { threshold: 0.3 }
        );

        counters.forEach(function (el) {
            observer.observe(el);
        });
    }
    animateCountUp();

    // ======================================================================
    // PREDICTION PAGE
    // ======================================================================

    var predictForm = document.getElementById("predict-form");
    if (!predictForm) return; // Not on the prediction page

    // ---- Slider display values --------------------------------------------
    var sliders = ["temp", "hum", "windspeed"];
    sliders.forEach(function (id) {
        var slider = document.getElementById(id);
        var display = document.getElementById(id + "-display");
        if (slider && display) {
            slider.addEventListener("input", function () {
                display.textContent = parseFloat(this.value).toFixed(2);
            });
        }
    });

    // Hour slider — custom time format
    var hrSlider = document.getElementById("hr");
    var hrDisplay = document.getElementById("hr-display");
    if (hrSlider && hrDisplay) {
        hrSlider.addEventListener("input", function () {
            hrDisplay.textContent = parseInt(this.value) + ":00";
        });
    }

    // ---- Data table rendering ---------------------------------------------
    var COLUMNS = [
        "season", "mnth", "hr", "holiday", "weekday",
        "workingday", "weathersit", "temp", "hum", "windspeed", "cnt"
    ];

    var testOffset = 0;
    var BATCH_SIZE = 200;

    function renderRows(tbody, rows, isTest) {
        rows.forEach(function (row) {
            var tr = document.createElement("tr");
            COLUMNS.forEach(function (col) {
                var td = document.createElement("td");
                var val = row[col];
                if (typeof val === "number" && col !== "cnt" && col !== "season" &&
                    col !== "mnth" && col !== "hr" && col !== "holiday" &&
                    col !== "weekday" && col !== "workingday" && col !== "weathersit") {
                    td.textContent = val.toFixed(2);
                } else {
                    td.textContent = val;
                }
                if (col === "cnt") td.classList.add("td-target");
                tr.appendChild(td);
            });

            if (isTest) {
                tr.addEventListener("click", function () {
                    fillFormFromRow(row);
                    // Highlight selected row
                    var prev = tbody.querySelector(".row-selected");
                    if (prev) prev.classList.remove("row-selected");
                    tr.classList.add("row-selected");
                    // Scroll to the Generate Forecast button
                    var btnPredict = document.getElementById("btn-predict");
                    if (btnPredict) {
                        btnPredict.scrollIntoView({ behavior: "smooth", block: "end" });
                    }
                });
            }

            tbody.appendChild(tr);
        });
    }

    function loadTestData() {
        fetch("/api/test-data?offset=" + testOffset + "&limit=" + BATCH_SIZE)
            .then(function (r) { return r.json(); })
            .then(function (data) {
                var tbody = document.getElementById("test-tbody");
                renderRows(tbody, data.data, true);
                testOffset += data.data.length;
                var countEl = document.getElementById("test-count");
                if (countEl) countEl.textContent = testOffset + " of " + data.total.toLocaleString() + " rows";
                var loadMoreBtn = document.getElementById("btn-load-more-test");
                if (loadMoreBtn && testOffset >= data.total) {
                    loadMoreBtn.style.display = "none";
                }
            })
            .catch(function () { });
    }

    // Initial load
    loadTestData();

    // Load more buttons
    var btnMoreTest = document.getElementById("btn-load-more-test");
    if (btnMoreTest) btnMoreTest.addEventListener("click", loadTestData);

    // ---- Fill form from data row ------------------------------------------
    function fillFormFromRow(row) {
        var fields = ["season", "mnth", "holiday", "weekday",
            "workingday", "weathersit"];
        fields.forEach(function (f) {
            var el = document.getElementById(f);
            if (el && row[f] !== undefined) el.value = row[f];
        });

        // Hour slider
        var hrEl = document.getElementById("hr");
        var hrDisp = document.getElementById("hr-display");
        if (hrEl && row.hr !== undefined) {
            hrEl.value = row.hr;
            if (hrDisp) hrDisp.textContent = parseInt(row.hr) + ":00";
        }

        // Sliders
        var sliderFields = ["temp", "hum", "windspeed"];
        sliderFields.forEach(function (f) {
            var el = document.getElementById(f);
            var display = document.getElementById(f + "-display");
            if (el && row[f] !== undefined) {
                el.value = row[f];
                if (display) display.textContent = parseFloat(row[f]).toFixed(2);
            }
        });

        // Store actual value for comparison
        var actualInput = document.getElementById("actual-value");
        if (actualInput && row.cnt !== undefined) {
            actualInput.value = row.cnt;
        }
    }

    // ---- Load random test sample ------------------------------------------
    var btnLoadSample = document.getElementById("btn-load-sample");
    if (btnLoadSample) {
        btnLoadSample.addEventListener("click", function () {
            btnLoadSample.disabled = true;
            btnLoadSample.textContent = "Loading...";
            fetch("/api/test-sample")
                .then(function (r) { return r.json(); })
                .then(function (sample) {
                    fillFormFromRow(sample);
                    btnLoadSample.disabled = false;
                    btnLoadSample.textContent = "Load Test Sample";

                })
                .catch(function () {
                    btnLoadSample.disabled = false;
                    btnLoadSample.textContent = "Load Test Sample";
                });
        });
    }

    // ---- Clear form -------------------------------------------------------
    var btnClear = document.getElementById("btn-clear-form");
    if (btnClear) {
        btnClear.addEventListener("click", function () {
            predictForm.reset();
            // Reset slider displays
            sliders.forEach(function (id) {
                var display = document.getElementById(id + "-display");
                var slider = document.getElementById(id);
                if (display && slider) display.textContent = parseFloat(slider.value).toFixed(2);
            });
            // Reset hour slider display
            var hrDisp = document.getElementById("hr-display");
            if (hrDisp) hrDisp.textContent = "12:00";
            document.getElementById("actual-value").value = "";
            var resultCard = document.getElementById("result-card");
            if (resultCard) resultCard.style.display = "none";
        });
    }

    // ---- Prediction form submit -------------------------------------------
    predictForm.addEventListener("submit", function (e) {
        e.preventDefault();

        var btnPredict = document.getElementById("btn-predict");
        var btnText = btnPredict.querySelector(".btn-text");
        var btnLoader = btnPredict.querySelector(".btn-loader");
        btnText.style.display = "none";
        btnLoader.style.display = "inline-flex";
        btnPredict.disabled = true;

        var payload = {};
        var fields = ["season", "mnth", "hr", "holiday", "weekday",
            "workingday", "weathersit", "temp", "hum", "windspeed"];
        fields.forEach(function (f) {
            var el = document.getElementById(f);
            if (el) payload[f] = parseFloat(el.value);
        });

        // Hardcode yr to 1 (mature demand level from training data)
        payload.yr = 1;

        var actualVal = document.getElementById("actual-value").value;
        if (actualVal !== "") {
            payload.actual = parseFloat(actualVal);
        }

        fetch("/api/predict", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                showResult(data);
            })
            .catch(function () {
                alert("Prediction failed. Please check the server.");
            })
            .finally(function () {
                btnText.style.display = "inline";
                btnLoader.style.display = "none";
                btnPredict.disabled = false;
            });
    });

    // ---- Show prediction result -------------------------------------------
    function showResult(data) {
        var resultCard = document.getElementById("result-card");
        resultCard.style.display = "none";

        // Force reflow for animation restart
        void resultCard.offsetWidth;
        resultCard.style.display = "block";

        // Trigger appearance animation each time
        resultCard.classList.remove("show");
        void resultCard.offsetWidth;
        resultCard.classList.add("show");

        // Animate the number counting up
        var resultValue = document.getElementById("result-value");
        // Add a subtle pulse on the number
        resultValue.classList.remove("pulse");
        void resultValue.offsetWidth;
        resultValue.classList.add("pulse");
        animateNumber(resultValue, 0, Math.round(data.prediction), 800);

        // Comparison section
        var compSection = document.getElementById("result-comparison");
        if (data.actual !== undefined && data.actual !== null) {
            compSection.style.display = "block";

            var maxVal = Math.max(data.prediction, data.actual, 1);

            // Predicted bar
            var barPredicted = document.getElementById("bar-predicted");
            var barPredVal = document.getElementById("bar-predicted-val");
            barPredicted.classList.remove("animate");
            barPredicted.style.width = "0%";
            barPredicted.style.setProperty("--bar-width", (data.prediction / maxVal * 100) + "%");
            barPredVal.textContent = Math.round(data.prediction);
            setTimeout(function () {
                barPredicted.classList.add("animate");
                barPredicted.style.width = (data.prediction / maxVal * 100) + "%";
            }, 100);

            // Actual bar
            var barActual = document.getElementById("bar-actual");
            var barActualVal = document.getElementById("bar-actual-val");
            barActual.classList.remove("animate");
            barActual.style.width = "0%";
            barActual.style.setProperty("--bar-width", (data.actual / maxVal * 100) + "%");
            barActualVal.textContent = Math.round(data.actual);
            setTimeout(function () {
                barActual.classList.add("animate");
                barActual.style.width = (data.actual / maxVal * 100) + "%";
            }, 300);

            // Error stats
            var errorAbs = document.getElementById("comp-error-abs");
            var errorPct = document.getElementById("comp-error-pct");
            errorAbs.classList.remove("animate");
            errorPct.classList.remove("animate");
            errorAbs.textContent = data.error_abs + " rentals";
            errorPct.textContent = data.error_pct + "%";
            setTimeout(function () {
                errorAbs.classList.add("animate");
                errorPct.classList.add("animate");
            }, 500);
        } else {
            compSection.style.display = "none";
        }

        // Scroll to result
        resultCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    function animateNumber(el, from, to, duration) {
        var startTime = null;
        function step(timestamp) {
            if (!startTime) startTime = timestamp;
            var progress = Math.min((timestamp - startTime) / duration, 1);
            var eased = 1 - Math.pow(1 - progress, 3);
            el.textContent = Math.round(from + (to - from) * eased).toLocaleString();
            if (progress < 1) {
                requestAnimationFrame(step);
            }
        }
        requestAnimationFrame(step);
    }


})();
