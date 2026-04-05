/**
 * quill-init.js  —  Initialise Quill rich-text editor for notes
 */

function initNoteEditor({ noteId, saveUrl, initJson }) {
  const toolbarOptions = [
    [{ header: [1, 2, 3, false] }],
    ["bold", "italic", "underline", "strike", "code"],
    [{ list: "ordered" }, { list: "bullet" }],
    [{ indent: "-1" }, { indent: "+1" }],
    ["blockquote", "code-block"],
    [{ color: [] }, { background: [] }],
    ["link", "image"],
    ["clean"],
  ];

  const quill = new Quill("#quill-editor", {
    theme: "snow",
    placeholder: "Start writing your notes here…",
    modules: { toolbar: toolbarOptions },
  });

  // Load existing content
  if (initJson) {
    try {
      const delta =
        typeof initJson === "string" ? JSON.parse(initJson) : initJson;
      quill.setContents(delta);
    } catch (_) {
      /* malformed JSON — ignore */
    }
  }

  const indicator = document.getElementById("save-indicator");
  let dirty = false;

  quill.on("text-change", function () {
    dirty = true;
    indicator.textContent = "Unsaved changes";
    indicator.style.color = "var(--accent)";
  });

  // Auto-save every 30 s if dirty and the note already exists
  if (saveUrl) {
    setInterval(function () {
      if (dirty) saveNote();
    }, 30_000);
  }

  window.saveNote = function () {
    const title =
      document.getElementById("note-title").value.trim() || "Untitled";
    const contentJson = JSON.stringify(quill.getContents());
    const contentPlain = quill.getText().trim();
    const subjectEl = document.getElementById("note-subject");
    const subjectId = subjectEl ? subjectEl.value || "" : "";

    if (saveUrl) {
      // AJAX save for existing note
      const formData = new FormData();
      formData.append(
        "csrf_token",
        document.querySelector('meta[name="csrf-token"]')?.content ||
          getCsrfFromCookie(),
      );
      formData.append("title", title);
      formData.append("content_json", contentJson);
      formData.append("content_plain", contentPlain);
      formData.append("subject_id", subjectId);

      fetch(saveUrl, { method: "POST", body: formData })
        .then((r) => r.json())
        .then(() => {
          dirty = false;
          indicator.textContent = "Saved";
          indicator.style.color = "var(--text-muted)";
          if (typeof showToast !== "undefined")
            showToast({ title: "Saved", message: "", type: "success" });
        })
        .catch(() => {
          if (typeof showToast !== "undefined")
            showToast({
              title: "Save failed",
              message: "Check connection.",
              type: "danger",
            });
        });
    } else {
      // New note — submit hidden form
      document.getElementById("form-title").value = title;
      document.getElementById("form-content-json").value = contentJson;
      document.getElementById("form-content-plain").value = contentPlain;
      document.getElementById("form-subject-id").value = subjectId;
      document.getElementById("new-note-form").submit();
    }
  };

  // Ctrl/Cmd+S keyboard shortcut
  document.addEventListener("keydown", function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key === "s") {
      e.preventDefault();
      window.saveNote();
    }
  });

  function getCsrfFromCookie() {
    return (
      document.cookie
        .split(";")
        .find((c) => c.trim().startsWith("csrf_"))
        ?.split("=")[1] || ""
    );
  }
}
