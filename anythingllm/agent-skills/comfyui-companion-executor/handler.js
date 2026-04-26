module.exports.runtime = {
  handler: async function ({
    userRequest,
    workflowApiJson,
    taskType,
    sourceImageUrl,
    preferInlineImage,
    cachedInstalledPacks,
    comfyuiBaseUrl,
    pollTimeoutSeconds,
    pollIntervalMs
  }) {
    const callerId = `${this.config.name}-v${this.config.version}`;
    const baseUrl = (comfyuiBaseUrl || "http://localhost:8188").replace(/\/+$/, "");
    const timeoutMs = Math.max(10000, Number(pollTimeoutSeconds || 120) * 1000);
    const intervalMs = Math.max(500, Number(pollIntervalMs || 1500));

    try {
      if (!userRequest || typeof userRequest !== "string") {
        return "Invalid input: userRequest must be a non-empty string.";
      }
      if (!workflowApiJson || typeof workflowApiJson !== "string") {
        return "Missing workflowApiJson. Provide a ComfyUI API workflow JSON string.";
      }

      const request = userRequest.trim();
      const normalized = request.toLowerCase();
      const inferredType = inferTaskType(normalized, taskType, sourceImageUrl);
      const selected = selectPack(normalized, inferredType);
      const clarifyingQuestions = buildClarifyingQuestions(inferredType, sourceImageUrl, request);
      if (clarifyingQuestions.length > 0) {
        return JSON.stringify({
          status: "needs-clarification",
          selectedPack: selected,
          questions: clarifyingQuestions
        });
      }

      const optimizedPrompt = optimizePrompt(request, selected.family);
      const negativePrompt = inferNegativePrompt(normalized);

      const cachePacks = parseCachedPacks(cachedInstalledPacks);
      const installState = checkInstallState(cachePacks, selected.selector);
      if (installState === "missing") {
        return JSON.stringify({
          status: "pack-missing",
          selectedPack: selected,
          message: `Selected pack '${selected.selector}' is not present in cachedInstalledPacks.`,
          action: `Add '${selected.selector}' to MODELS_DOWNLOAD and restart, or provide an installed alternative.`
        });
      }

      const parsedWorkflow = parseWorkflow(workflowApiJson);
      if (!parsedWorkflow.ok) {
        return `Invalid workflowApiJson: ${parsedWorkflow.error}`;
      }

      const hydrated = applyPlaceholders(parsedWorkflow.workflow, {
        prompt: optimizedPrompt,
        negative: negativePrompt,
        sourceImageUrl: sourceImageUrl || ""
      });

      this.introspect(`${callerId}: submitting ComfyUI prompt`);
      const submit = await submitPrompt(baseUrl, hydrated);
      if (!submit.ok) {
        return `ComfyUI submit failed: ${submit.error}`;
      }

      const history = await pollHistory(baseUrl, submit.promptId, timeoutMs, intervalMs);
      if (!history.ok) {
        return `ComfyUI execution failed: ${history.error}`;
      }

      const images = extractImages(history.data, submit.promptId);
      const links = images.map((img) => ({
        filename: img.filename,
        viewUrl: `${baseUrl}/view?filename=${encodeURIComponent(img.filename)}&subfolder=${encodeURIComponent(img.subfolder || "")}&type=${encodeURIComponent(img.type || "output")}`
      }));

      const inlinePreferred = preferInlineImage !== false;
      const inlineMarkdown = inlinePreferred && links.length > 0 ? `![render](${links[0].viewUrl})` : null;

      const result = {
        status: "completed",
        selectedPack: selected,
        promptId: submit.promptId,
        installCheck: {
          state: installState,
          note:
            installState === "unknown"
              ? "Pack not confirmed from cache. Keep cachedInstalledPacks updated from RAG."
              : "Pack confirmed from cachedInstalledPacks."
        },
        optimizedPrompt,
        negativePrompt,
        output: {
          inlinePreferred,
          inlineMarkdown,
          downloadLinks: links.map((l) => `Download image: ${l.viewUrl}`)
        },
        metadata: {
          imageCount: links.length,
          baseUrl
        }
      };

      return JSON.stringify(result);
    } catch (e) {
      this.logger(`${callerId} failed`, e.message);
      return `ComfyUI companion executor failed: ${e.message}`;
    }
  }
};

function inferTaskType(normalized, explicitTask, sourceImageUrl) {
  const t = (explicitTask || "").toLowerCase();
  if (["t2i", "edit", "video", "3d", "audio"].includes(t)) return t;
  if (sourceImageUrl) return "edit";
  if (/inpaint|outpaint|img2img|edit|remove|replace background/.test(normalized)) return "edit";
  if (/video|t2v|i2v/.test(normalized)) return "video";
  if (/3d|mesh|asset/.test(normalized)) return "3d";
  if (/audio|music|song/.test(normalized)) return "audio";
  return "t2i";
}

function selectPack(normalized, requestType) {
  if (requestType === "video") {
    return { selector: "wan-2-2", family: "video", reason: "Default video route." };
  }
  if (requestType === "3d") {
    if (/gguf|low vram|low-vram/.test(normalized)) {
      return { selector: "trellis2-gguf", family: "3d", reason: "Low-memory 3D route." };
    }
    return { selector: "hunyuan-3d", family: "3d", reason: "Default 3D route." };
  }
  if (requestType === "audio") {
    return { selector: "ace-step", family: "audio", reason: "Audio route." };
  }
  if (requestType === "edit") {
    if (/fast|quick/.test(normalized)) {
      return { selector: "sdxl-lightning", family: "sdxl-lightning", reason: "Fast edit route." };
    }
    return { selector: "sdxl-editing", family: "sdxl-editing", reason: "Editing route." };
  }
  if (/anime|manga|waifu/.test(normalized)) {
    return { selector: "newbie-image", family: "newbie-image", reason: "Anime route." };
  }
  if (/text|logo|poster|sign|typography/.test(normalized)) {
    return { selector: "ovis-image", family: "ovis-image", reason: "Text-rendering route." };
  }
  if (/highest|premium|cinematic|natural/.test(normalized)) {
    return { selector: "flux1-krea", family: "flux-krea", reason: "High realism route." };
  }
  return { selector: "klein-distilled", family: "flux-klein", reason: "Default photoreal/general route." };
}

function buildClarifyingQuestions(requestType, sourceImageUrl, request) {
  const q = [];
  const lower = request.toLowerCase();
  const hasSize = /16:9|9:16|1:1|4:5|3:2|1024|768|512|landscape|portrait/.test(lower);
  const hasStyle = /anime|photo|photoreal|cinematic|illustration|style/.test(lower);
  if (requestType === "t2i") {
    if (!hasStyle) q.push("What style do you want (anime, photoreal, cinematic, illustration)?");
    if (!hasSize) q.push("What aspect ratio or resolution should I render?");
  }
  if (requestType === "edit") {
    if (!sourceImageUrl) q.push("Provide the source image URL/path.");
    q.push("Which areas must be preserved and which areas should change?");
  }
  return q.slice(0, 4);
}

function optimizePrompt(input, family) {
  if (family === "newbie-image") return `${input}\nAnime-focused attributes, clean tags, avoid photoreal wording.`;
  if (family === "ovis-image")
    return `${input}\nInclude exact quoted text and placement details for legibility.`;
  if (family === "sdxl-lightning")
    return `${input}\nKeep concise for fast low-step SDXL Lightning inference.`;
  if (family === "sdxl-editing")
    return `${input}\nDescribe surgical edits while preserving non-target regions.`;
  if (family === "flux-klein" || family === "flux-krea")
    return `${input}\nUse concrete composition, lighting, and material details.`;
  return input;
}

function inferNegativePrompt(normalized) {
  if (/anime|manga/.test(normalized)) {
    return "low quality, blurry, bad anatomy, extra limbs, watermark, text artifacts";
  }
  return "low quality, blurry, watermark, text artifacts, deformed";
}

function parseCachedPacks(cachedInstalledPacks) {
  if (!cachedInstalledPacks || typeof cachedInstalledPacks !== "string") return [];
  try {
    const parsed = JSON.parse(cachedInstalledPacks);
    return Array.isArray(parsed) ? parsed.filter((x) => typeof x === "string") : [];
  } catch (_e) {
    return [];
  }
}

function checkInstallState(cachePacks, selectedSelector) {
  if (!cachePacks || cachePacks.length === 0) return "unknown";
  return cachePacks.includes(selectedSelector) ? "installed" : "missing";
}

function parseWorkflow(workflowApiJson) {
  try {
    const workflow = JSON.parse(workflowApiJson);
    if (!workflow || typeof workflow !== "object") {
      return { ok: false, error: "workflow must be a JSON object" };
    }
    return { ok: true, workflow };
  } catch (e) {
    return { ok: false, error: e.message };
  }
}

function applyPlaceholders(workflow, values) {
  return deepMap(workflow, (v) => {
    if (typeof v !== "string") return v;
    return v
      .replaceAll("__PROMPT__", values.prompt)
      .replaceAll("__NEGATIVE__", values.negative)
      .replaceAll("__SOURCE_IMAGE_URL__", values.sourceImageUrl);
  });
}

function deepMap(value, mapper) {
  if (Array.isArray(value)) return value.map((v) => deepMap(v, mapper));
  if (value && typeof value === "object") {
    const out = {};
    for (const key of Object.keys(value)) {
      out[key] = deepMap(value[key], mapper);
    }
    return out;
  }
  return mapper(value);
}

async function submitPrompt(baseUrl, workflow) {
  try {
    const res = await fetch(`${baseUrl}/prompt`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: workflow })
    });
    if (!res.ok) return { ok: false, error: `HTTP ${res.status}` };
    const data = await res.json();
    if (!data || !data.prompt_id) return { ok: false, error: "Missing prompt_id in response." };
    return { ok: true, promptId: data.prompt_id };
  } catch (e) {
    return { ok: false, error: e.message };
  }
}

async function pollHistory(baseUrl, promptId, timeoutMs, intervalMs) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(`${baseUrl}/history/${encodeURIComponent(promptId)}`, { method: "GET" });
      if (res.ok) {
        const data = await res.json();
        if (data && data[promptId]) return { ok: true, data };
      }
    } catch (_e) {
      // Continue polling.
    }
    await sleep(intervalMs);
  }
  return { ok: false, error: `Timed out after ${timeoutMs}ms waiting for prompt ${promptId}.` };
}

function extractImages(historyData, promptId) {
  const promptRecord = historyData[promptId];
  if (!promptRecord || !promptRecord.outputs) return [];
  const images = [];
  const outputNodeIds = Object.keys(promptRecord.outputs);
  for (const nodeId of outputNodeIds) {
    const out = promptRecord.outputs[nodeId];
    if (!out || !Array.isArray(out.images)) continue;
    for (const image of out.images) {
      if (!image || !image.filename) continue;
      images.push({
        filename: image.filename,
        subfolder: image.subfolder || "",
        type: image.type || "output"
      });
    }
  }
  return images;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
