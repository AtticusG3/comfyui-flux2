module.exports.runtime = {
  handler: async function ({
    userRequest,
    taskType,
    sourceImageUrl,
    preferInlineImage,
    cachedInstalledPacks,
    comfyuiBaseUrl
  }) {
    const callerId = `${this.config.name}-v${this.config.version}`;
    const baseUrl = (comfyuiBaseUrl || "http://localhost:8188").replace(/\/+$/, "");

    try {
      if (!userRequest || typeof userRequest !== "string") {
        return "Invalid input: userRequest must be a non-empty string.";
      }

      const request = userRequest.trim();
      const normalized = request.toLowerCase();
      const explicitTask = (taskType || "").toLowerCase();

      const packs = [
        {
          selector: "newbie-image",
          aliases: ["newbie-image", "newbie", "newbieimage"],
          supports: ["t2i"],
          intentTags: ["anime", "manga", "waifu", "illustration"],
          family: "newbie-image"
        },
        {
          selector: "klein-distilled",
          aliases: ["klein-distilled", "flux2-klein", "klein"],
          supports: ["t2i", "edit"],
          intentTags: ["photo", "photoreal", "portrait", "product", "realistic"],
          family: "flux-klein"
        },
        {
          selector: "flux1-krea",
          aliases: ["flux1-krea", "krea", "flux-krea"],
          supports: ["t2i", "edit"],
          intentTags: ["cinematic", "natural", "premium realism", "high realism"],
          family: "flux-krea"
        },
        {
          selector: "ovis-image",
          aliases: ["ovis-image", "ovis", "ovisimage"],
          supports: ["t2i"],
          intentTags: ["text", "typography", "poster", "logo", "sign", "bilingual"],
          family: "ovis-image"
        },
        {
          selector: "sdxl-lightning",
          aliases: ["sdxl-lightning", "lightning", "sdxl", "photo-sdxl"],
          supports: ["t2i", "edit"],
          intentTags: ["fast", "quick", "sdxl", "photo"],
          family: "sdxl-lightning"
        },
        {
          selector: "sdxl-editing",
          aliases: ["sdxl-editing", "sdxl-edit", "sdxl-inpaint"],
          supports: ["edit", "t2i"],
          intentTags: ["inpaint", "outpaint", "img2img", "edit", "mask"],
          family: "sdxl-editing"
        },
        {
          selector: "hunyuan-video",
          aliases: ["hunyuan-video", "hyvideo"],
          supports: ["video"],
          intentTags: ["video", "t2v", "i2v"],
          family: "video"
        },
        {
          selector: "wan-2-2",
          aliases: ["wan-2-2", "wan", "wan22"],
          supports: ["video"],
          intentTags: ["video", "camera control", "fun inpaint"],
          family: "video"
        },
        {
          selector: "hunyuan-3d",
          aliases: ["hunyuan-3d", "hunyuan3d"],
          supports: ["3d"],
          intentTags: ["3d", "mesh", "asset"],
          family: "3d"
        },
        {
          selector: "trellis2-gguf",
          aliases: ["trellis2-gguf", "trellis2", "trellis"],
          supports: ["3d"],
          intentTags: ["3d", "gguf"],
          family: "3d"
        },
        {
          selector: "ace-step",
          aliases: ["ace-step", "acestep"],
          supports: ["audio"],
          intentTags: ["music", "audio", "song"],
          family: "audio"
        },
        {
          selector: "vram-utils",
          aliases: ["vram-utils", "vram", "cleanup"],
          supports: ["utility"],
          intentTags: ["cleanup", "offload", "memory"],
          family: "utility"
        }
      ];

      const inferredType = inferTaskType(normalized, explicitTask, sourceImageUrl);
      const selectedPack = selectPack(packs, normalized, inferredType);
      const clarifyingQuestions = buildClarifyingQuestions(inferredType, sourceImageUrl, request);
      const optimizedPrompt = optimizePrompt(request, selectedPack.family);

      this.introspect(`${callerId}: selected pack ${selectedPack.selector}`);

      let installedFromCache = parseCachedPacks(cachedInstalledPacks);
      let installState = "unknown";
      let installEvidence = "No pack cache found.";

      if (installedFromCache.length > 0) {
        const hasPack = installedFromCache.includes(selectedPack.selector);
        installState = hasPack ? "installed" : "missing";
        installEvidence = hasPack
          ? `Found '${selectedPack.selector}' in cachedInstalledPacks (RAG/memory).`
          : `Cached installed packs did not include '${selectedPack.selector}'.`;
      } else {
        const liveCheck = await probeComfyUi(baseUrl);
        if (liveCheck.reachable) {
          installEvidence = "ComfyUI API reachable. Exact pack install status requires cached pack list or user confirmation.";
        } else {
          installEvidence = `Could not reach ComfyUI API at ${baseUrl}: ${liveCheck.reason}`;
        }
      }

      const result = {
        action: "comfyui-companion-routing",
        requestType: inferredType,
        selectedPack: {
          selector: selectedPack.selector,
          reason: selectedPack.reason
        },
        knownPacks: packs.map((p) => ({
          selector: p.selector,
          supports: p.supports
        })),
        installCheck: {
          state: installState,
          evidence: installEvidence,
          needsUserConfirmation: installState === "unknown" || installState === "missing"
        },
        clarification: {
          required: clarifyingQuestions.length > 0,
          questions: clarifyingQuestions
        },
        promptOptimization: {
          modelFamily: selectedPack.family,
          optimizedPrompt
        },
        rendering: {
          mode: preferInlineImage === false ? "download-link" : "inline-preferred",
          instruction:
            preferInlineImage === false
              ? "Return a direct download link/path to output image."
              : "Try markdown inline image first: ![render](URL). If chat cannot render, provide `Download image: URL`."
        },
        nextStepInstruction:
          "If clarification is required, ask questions first. Otherwise submit ComfyUI workflow via POST /prompt, poll GET /history/{prompt_id}, then return inline image or download link with metadata.",
        apiHints: {
          baseUrl,
          endpoints: ["POST /prompt", "GET /history/{prompt_id}", "GET /object_info", "POST /free", "/ws"]
        }
      };

      return JSON.stringify(result);
    } catch (e) {
      this.logger(`${callerId} failed`, e.message);
      return `ComfyUI companion skill failed: ${e.message}`;
    }
  }
};

function inferTaskType(normalized, explicitTask, sourceImageUrl) {
  if (explicitTask === "edit") return "edit";
  if (explicitTask === "t2i") return "t2i";
  if (explicitTask === "video") return "video";
  if (explicitTask === "3d") return "3d";
  if (explicitTask === "audio") return "audio";
  if (sourceImageUrl) return "edit";
  if (/inpaint|outpaint|img2img|edit|remove|replace background/.test(normalized)) return "edit";
  if (/video|t2v|i2v/.test(normalized)) return "video";
  if (/3d|mesh|asset/.test(normalized)) return "3d";
  if (/music|audio|song/.test(normalized)) return "audio";
  return "t2i";
}

function selectPack(packs, normalized, requestType) {
  const compatible = packs.filter((p) => p.supports.includes(requestType));
  if (compatible.length === 0) {
    return {
      selector: "klein-distilled",
      family: "flux-klein",
      reason: "Fallback default pack."
    };
  }

  if (requestType === "t2i" || requestType === "edit") {
    if (/anime|manga|waifu/.test(normalized) && requestType === "t2i") {
      return {
        selector: "newbie-image",
        family: "newbie-image",
        reason: "Anime intent detected. Newbie is preferred."
      };
    }
    if (/text|logo|poster|sign|typography|caption/.test(normalized) && requestType === "t2i") {
      return {
        selector: "ovis-image",
        family: "ovis-image",
        reason: "Text rendering intent detected. Ovis is preferred."
      };
    }
    if (requestType === "edit") {
      if (/fast|quick/.test(normalized)) {
        return {
          selector: "sdxl-lightning",
          family: "sdxl-lightning",
          reason: "Edit task with speed preference."
        };
      }
      return {
        selector: "sdxl-editing",
        family: "sdxl-editing",
        reason: "Edit task defaults to SDXL editing workflows."
      };
    }
    if (/highest|premium|cinematic|natural/.test(normalized)) {
      return {
        selector: "flux1-krea",
        family: "flux-krea",
        reason: "High realism quality intent."
      };
    }
    return {
      selector: "klein-distilled",
      family: "flux-klein",
      reason: "Default photoreal/general image route."
    };
  }

  if (requestType === "video") {
    if (/camera|fun|inpaint/.test(normalized)) {
      return {
        selector: "wan-2-2",
        family: "video",
        reason: "Wan 2.2 supports richer video controls."
      };
    }
    return {
      selector: "wan-2-2",
      family: "video",
      reason: "Default video route."
    };
  }

  if (requestType === "3d") {
    if (/gguf|low vram|low-vram/.test(normalized)) {
      return {
        selector: "trellis2-gguf",
        family: "3d",
        reason: "3D request with low-memory/gguf hint."
      };
    }
    return {
      selector: "hunyuan-3d",
      family: "3d",
      reason: "Default 3D route."
    };
  }

  if (requestType === "audio") {
    return {
      selector: "ace-step",
      family: "audio",
      reason: "Audio/music request route."
    };
  }

  return {
    selector: "klein-distilled",
    family: "flux-klein",
    reason: "Fallback default route."
  };
}

function buildClarifyingQuestions(requestType, sourceImageUrl, request) {
  const questions = [];
  const hasAspect = /16:9|9:16|1:1|4:5|3:2|landscape|portrait/.test(request.toLowerCase());
  const hasStyle = /style|anime|photo|cinematic|oil|watercolor|realistic|illustration/.test(
    request.toLowerCase()
  );

  if (requestType === "t2i") {
    if (!hasStyle) questions.push("What style do you want (anime, photoreal, cinematic, illustration)?");
    if (!hasAspect) questions.push("What aspect ratio/resolution should I use?");
    questions.push("Any elements to avoid (negative constraints)?");
  }

  if (requestType === "edit") {
    if (!sourceImageUrl) questions.push("Please provide the source image URL/path for editing.");
    questions.push("Which regions must be preserved exactly?");
    questions.push("Do you want subtle edit or strong transformation?");
  }

  if (requestType === "video") {
    questions.push("Target duration, fps, and resolution?");
    questions.push("Text-to-video or image-to-video?");
  }

  return questions.slice(0, 5);
}

function optimizePrompt(input, modelFamily) {
  if (modelFamily === "newbie-image") {
    return `${input}\nUse clean anime descriptors, clear character attributes, and avoid photoreal wording.`;
  }
  if (modelFamily === "ovis-image") {
    return `${input}\nIf text is required, include exact quoted text and placement/typography instructions.`;
  }
  if (modelFamily === "sdxl-lightning") {
    return `${input}\nKeep prompt concise and direct for low-step SDXL Lightning inference.`;
  }
  if (modelFamily === "sdxl-editing") {
    return `${input}\nDescribe only intended edits and preserve non-target regions.`;
  }
  if (modelFamily === "flux-krea" || modelFamily === "flux-klein") {
    return `${input}\nUse concrete composition, lighting, lens/material details, and coherent natural language.`;
  }
  return input;
}

function parseCachedPacks(cachedInstalledPacks) {
  if (!cachedInstalledPacks || typeof cachedInstalledPacks !== "string") return [];
  try {
    const parsed = JSON.parse(cachedInstalledPacks);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((x) => typeof x === "string").map((x) => x.trim());
  } catch (_e) {
    return [];
  }
}

async function probeComfyUi(baseUrl) {
  try {
    const res = await fetch(`${baseUrl}/object_info`, { method: "GET" });
    if (!res.ok) {
      return { reachable: false, reason: `HTTP ${res.status}` };
    }
    return { reachable: true };
  } catch (e) {
    return { reachable: false, reason: e.message };
  }
}
