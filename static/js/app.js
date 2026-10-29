(() => {
  const form = document.querySelector("#upload-form");
  const input = document.querySelector("#resume-file");
  const dropZone = document.querySelector("#drop-zone");
  const dropTitle = document.querySelector("#drop-title");
  const dropSubtitle = document.querySelector("#drop-subtitle");
  const parseButton = document.querySelector("#parse-button");
  const statusMessage = document.querySelector("#status-message");
  const emptyState = document.querySelector("#empty-state");
  const resultsContent = document.querySelector("#results-content");
  const candidateResults = document.querySelector("#candidate-results");
  const rawJson = document.querySelector("#raw-json");
  const jsonToggle = document.querySelector("#json-toggle");
  let latestResult = null;

  const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);

  function showStatus(message, success = false) {
    statusMessage.textContent = message;
    statusMessage.hidden = !message;
    statusMessage.classList.toggle("success", success);
  }

  function selectFile(file) {
    if (!file) return;
    const extension = file.name.split(".").pop().toLowerCase();
    if (!["pdf", "docx", "txt"].includes(extension)) {
      input.value = "";
      parseButton.disabled = true;
      showStatus("Please choose a PDF, DOCX or TXT file.");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      input.value = "";
      parseButton.disabled = true;
      showStatus("This file exceeds the 5 MB upload limit.");
      return;
    }
    dropTitle.textContent = file.name;
    dropSubtitle.innerHTML = `${(file.size / 1024 / 1024).toFixed(2)} MB · <span>Click to change</span>`;
    parseButton.disabled = false;
    showStatus("");
  }

  input.addEventListener("change", () => selectFile(input.files[0]));
  ["dragenter", "dragover"].forEach((eventName) => dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.add("dragover");
  }));
  ["dragleave", "drop"].forEach((eventName) => dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.remove("dragover");
  }));
  dropZone.addEventListener("drop", (event) => {
    const file = event.dataTransfer.files[0];
    if (!file) return;
    const transfer = new DataTransfer();
    transfer.items.add(file);
    input.files = transfer.files;
    selectFile(file);
  });

  function listCard(title, items, formatter = (item) => escapeHtml(item)) {
    if (!items?.length) return "";
    return `<section class="candidate-card result-card"><h3>${title}</h3><div class="card-items">${items.map(formatter).join("")}</div></section>`;
  }

  function renderCandidate(candidate) {
    const contacts = [
      candidate.email && `<span>${escapeHtml(candidate.email)}</span>`,
      candidate.phone && `<span>${escapeHtml(candidate.phone)}</span>`,
      candidate.linkedin && `<a href="${escapeHtml(candidate.linkedin)}" target="_blank" rel="noopener noreferrer">LinkedIn</a>`,
      candidate.github && `<a href="${escapeHtml(candidate.github)}" target="_blank" rel="noopener noreferrer">GitHub</a>`,
    ].filter(Boolean).join("");
    candidateResults.innerHTML = `
      <section class="candidate-card">
        <h3 class="candidate-name">${escapeHtml(candidate.name || "Candidate")}</h3>
        <div class="candidate-meta">${contacts || "<span>No contact details detected</span>"}</div>
      </section>
      ${listCard("Skills", candidate.skills, (skill) => `<span class="skill-tag">${escapeHtml(skill)}</span>`)}
      ${listCard("Experience", candidate.experience, (item) => `<p>${escapeHtml(item.title)}${item.dates?.length ? ` · ${escapeHtml(item.dates.join(" – "))}` : ""}</p>`)}
      ${candidate.total_years_experience ? `<section class="candidate-card result-card"><h3>Experience duration</h3><p>${candidate.total_years_experience}+ years (estimated)</p></section>` : ""}
      ${listCard("Education", candidate.education, (item) => `<p>${escapeHtml([item.degree, item.institution, item.dates?.join(" – ")].filter(Boolean).join(" · "))}</p>`)}
      ${listCard("Projects", candidate.projects)}
      ${listCard("Certifications", candidate.certifications)}`;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const file = input.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    parseButton.disabled = true;
    parseButton.innerHTML = '<span class="spinner" aria-hidden="true"></span> Parsing…';
    showStatus("Analyzing resume sections and candidate details…", true);
    try {
      const response = await fetch("/api/parse", { method: "POST", body: formData });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Resume parsing failed.");
      latestResult = result.candidate;
      renderCandidate(latestResult);
      rawJson.textContent = JSON.stringify(latestResult, null, 2);
      rawJson.hidden = true;
      jsonToggle.setAttribute("aria-expanded", "false");
      jsonToggle.innerHTML = "View raw JSON <span>↗</span>";
      emptyState.hidden = true;
      resultsContent.hidden = false;
      showStatus("Resume parsed successfully.", true);
    } catch (error) {
      showStatus(error.message || "Unable to parse this resume. Please try another file.");
    } finally {
      parseButton.disabled = false;
      parseButton.innerHTML = 'Parse resume <span aria-hidden="true">→</span>';
    }
  });

  jsonToggle.addEventListener("click", () => {
    const expanded = jsonToggle.getAttribute("aria-expanded") === "true";
    jsonToggle.setAttribute("aria-expanded", String(!expanded));
    rawJson.hidden = expanded;
    jsonToggle.innerHTML = expanded ? 'View raw JSON <span>↗</span>' : 'Hide raw JSON <span>↙</span>';
  });
})();
