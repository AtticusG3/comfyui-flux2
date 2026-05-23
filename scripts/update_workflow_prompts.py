import json
from pathlib import Path


SDXL_NEG = (
    "worst quality, low quality, normal quality, jpeg artifacts, blurry, "
    "watermark, signature, text overlay, deformed, bad anatomy, extra fingers, "
    "mutated hands, disfigured, (poorly drawn hands:1.3), bad proportions, "
    "cropped, out of frame, overexposed, underexposed"
)
VIDEO_NEG = (
    "blurry, low quality, watermark, text, distorted motion, flickering, "
    "inconsistent lighting, morphing faces, extra limbs"
)
ANIME_NEG = (
    "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, "
    "fewer digits, cropped, worst quality, low quality, normal quality, jpeg "
    "artifacts, signature, watermark, username, blurry, artist name"
)


SCENES = {
    "workflows/flux2/klein-9b-t2i.json": (
        "A Nissan Silvia S15 Spec-R in metallic pearl white parked in front of a closed Daikoku Futo "
        "style warehouse, sodium vapor lights, light rain, wide-angle automotive photograph",
        "",
    ),
    "workflows/flux2/klein-9b-edit.json": (
        "Turn the car into a midnight purple widebody build with carbon canards and a large rear wing, "
        "keep license plate and stance, same environment and lighting",
        "",
    ),
    "workflows/sdxl-lightning/sdxl-lightning-t2i.json": (
        "A Toyota Supra MK4 A80 drifting through a hairpin on the Nurburgring dressed in Japanese livery, "
        "twin-turbo exhaust flames, Rising Sun flag hood wrap, motion blur on tyres, race marshal in background, "
        "overcast dramatic sky, professional motorsport photography, telephoto lens compression, ultra sharp",
        SDXL_NEG,
    ),
    "workflows/sdxl-lightning/sdxl-lightning-hires.json": (
        "Shibuya crossing at 3am during a typhoon, a heavily modified Honda NSX-R C30 with Kanjo style livery "
        "rolling through standing water, reflections of red and white traffic lights on the flooded road surface, "
        "background figures with umbrellas, cinematic anamorphic bokeh, Hasselblad medium-format texture, photorealistic",
        SDXL_NEG,
    ),
    "workflows/flux1-krea/flux-krea-t2i.json": (
        "A Kawasaki Z900RS Cafe Racer in candy green standing on the forecourt of a 1970s Showa-era petrol station "
        "in rural Hokkaido, analogue pump with hiragana labels, elderly station attendant in company uniform bowing, "
        "late autumn maples surrounding the scene, Kodak Portra 400 film emulation, slight halation on highlights",
        "",
    ),
    "workflows/newbie-image/newbie-image-t2i-low.json": (
        "<subject>Miku Hatsune wearing a racing queen uniform in black and gold, holding a chequered flag</subject> "
        "<background>paddock of a Super GT race at Fuji Speedway, rows of GT500 cars with Kanji liveries, Mount Fuji visible</background> "
        "<style>high-detail anime illustration, vibrant cel-shading, dynamic composition</style> "
        "<quality>masterpiece, best quality, 8k, sharp</quality>",
        ANIME_NEG,
    ),
    "workflows/newbie-image/newbie-image-t2i-high.json": (
        "<subject>Motoko Kusanagi in Section 9 tactical suit crouching on the roof of a neon-lit Cyberpunk Osaka skyscraper, "
        "Seburo C-26A in hand, rain-soaked</subject> <background>neo-Tokyo megacity sprawl below, holographic advertisements "
        "in Japanese floating in mid-air, flying vehicles</background> <pose>dynamic action crouch, looking over shoulder, "
        "wind catching hair</pose> <style>Ghost in the Shell anime aesthetic, Mamoru Oshii colour palette</style> "
        "<quality>masterpiece, best quality</quality>",
        ANIME_NEG,
    ),
    "workflows/ovis-image/ovis-t2i.json": (
        "A bold Japanese drift event poster, foreground shows a widebody Mazda RX-7 FD in aggressive stance mid-drift with tyre smoke, "
        "background is a night race circuit with stadium lights, large text reads DRIFT MATSURI 2025 in stylised English and below it "
        "走り屋の祭り in bold gothic kanji, event details text Ebisu Circuit • Fukushima • August at the bottom, clean graphic design, "
        "high contrast, professional print quality",
        ANIME_NEG,
    ),
    "workflows/wan-2-2/wan22-5b-t2v.json": (
        "A Toyota AE86 Trueno being driven up a mountain touge road in Gunma at dawn, drifting through tight S-curves surrounded by "
        "cryptomeria cedar forest, dramatic tyre smoke catching the first rays of sunrise, cinematic wide tracking shot, camera mounted "
        "low at road level, smooth consistent motion",
        VIDEO_NEG,
    ),
    "workflows/wan-2-2/wan22-5b-i2v.json": (
        "The driver's hands grip the D-shaped steering wheel of an AE86, gearstick shifts, revs visible on the analogue tachometer "
        "climbing to 8000rpm, dashboard shaking, Gunma mountain road hairpin visible through the windscreen, handheld camera feel, "
        "consistent interior detail throughout",
        VIDEO_NEG,
    ),
    "workflows/wan-2-2/wan22-14b-t2v.json": (
        "A JGTC 2001 grid start at Suzuka Circuit, Castrol Tom's Supra and Xanavi Nismo GT-R lined up alongside GT300 cars, dramatic "
        "wide establishing shot looking down the main straight, team crews watching, crowd packed grandstands, Fuji Bank logo visible "
        "on bridges, cinematic broadcast quality, consistent motion throughout all vehicles and people",
        VIDEO_NEG,
    ),
    "workflows/wan-2-2/wan22-14b-i2v.json": (
        "Animate this scene: the driver of the Supra raises his helmet visor and gives a thumbs up to the camera, steam rises from the "
        "car's hood post-race, mechanics run toward it, confetti begins falling from above, natural crowd movement in background, "
        "broadcast-quality video motion",
        VIDEO_NEG,
    ),
    "workflows/wan-2-2/wan22-14b-inpaint.json": (
        "The car in the foreground transforms, its paint fades from white to the iconic black-and-gold Keiichi Tsuchiya Levin livery, "
        "土屋圭市 kanji on the door appears, the transformation is smooth and cinematic, all other scene elements remain unchanged, "
        "consistent motion",
        VIDEO_NEG,
    ),
    "workflows/wan-2-2/wan22-14b-camera.json": (
        "An Initial D style downhill chase through Hakone at night, an RX-7 Spirit R and a Lan-Evo IX weave through switchbacks while the "
        "camera transitions from roof-mounted POV to roadside tracking and then aerial reveal, roadside vending machines glow in the mist, "
        "authentic touge atmosphere, smooth coherent motion",
        VIDEO_NEG,
    ),
    "workflows/ace-step/ace-step-t2m.json": (
        "Japanese city pop, 1980s Shibuya-kei style, driving synth bass, Rhodes electric piano, brushed jazz drumkit, warm tape saturation, "
        "female Japanese vocal hooks, late-night cruise vibes, 108 BPM, key of F major",
        "",
    ),
    "workflows/hunyuan-3d/hunyuan3d-i2-3d.json": (
        "Highly detailed 3D model of a Nissan Silvia S15 Spec-R, clean studio three-quarter front view, Brilliant Blue pearl paint, stock "
        "body kit, chrome RAYS VOLK TE37 wheels, clean topology suitable for a game asset pipeline",
        "",
    ),
    "workflows/z-anime/z-anime-t2i.json": (
        "A young anime pilot girl in a crisp white JASDF-style flight suit standing on the deck of a fictional carrier at sunset, "
        "F-2 inspired trainer behind her with kanji roundels, warm rim light, detailed anime illustration, cinematic vertical composition",
        ANIME_NEG,
    ),
    "workflows/z-image-turbo/z-turbo-t2i.json": (
        "Photorealistic night photograph of a Toyota GR Yaris Circuit Edition in Emotional Red II parked on a Hakone hairpin, "
        "light rain, guardrail reflections, long exposure light trails from distant traffic, 35mm lens look",
        "",
    ),
    "workflows/z-image-turbo/z-base-t2i.json": (
        "Studio lit product shot of a carbon-kevlar racing helmet with subtle Mount Fuji line art, matte finish, neutral grey sweep, "
        "sharp focus, commercial automotive photography",
        "",
    ),
    "workflows/ernie-image/ernie-sft-t2i.json": (
        "Watercolor travel poster of Kanazawa Higashi Chaya district at dusk, paper grain, soft edges, muted indigo and ochre palette, "
        "small silhouettes of tourists, vintage railway typography in corner",
        "",
    ),
    "workflows/ernie-image/ernie-turbo-t2i.json": (
        "Bold vector travel sticker of a shinkansen nose cone in cobalt and white, thick white outline, flat colors, minimal shadows, "
        "suitable for print on a laptop skin",
        "",
    ),
    "workflows/firered-image-edit/firered-edit.json": (
        "Change the jacket to a bright indigo technical shell with reflective piping, keep pose and background, realistic fabric folds",
        "",
    ),
    "workflows/flux2/klein-4b-t2i.json": (
        "A Nissan Silvia S15 Spec-R in metallic pearl white, low VRAM 4B Klein path, "
        "sodium vapor lights, light rain, wide-angle automotive photograph",
        "",
    ),
    "workflows/flux2/klein-4b-edit.json": (
        "Turn the car into a midnight purple widebody build, keep environment and lighting, 4B Klein edit",
        "",
    ),
    "workflows/qwen-image-edit-2511/qwen-edit-2511.json": (
        "Change the jacket to a bright indigo technical shell with reflective piping, keep pose and background",
        "",
    ),
    "workflows/realvisxl/realvisxl-lightning-t2i.json": (
        "A classic Nissan Skyline GT-R R32 in gunmetal grey at Daikoku PA, gritty urban night photography",
        SDXL_NEG,
    ),
    "workflows/realvisxl/realvisxl-v5-hires.json": (
        "Shibuya crossing at 3am, modified Honda NSX-R, photorealistic hires pass",
        SDXL_NEG,
    ),
    "workflows/hidream-o1/hidream-o1-example.json": (
        "A cinematic portrait of a woman in a red coat standing in neon rain, editorial photography",
        "",
    ),
    "workflows/hunyuan-video/hunyuan-video-guide.json": (
        "A cat walking on a beach at sunset, gentle waves, cinematic motion",
        VIDEO_NEG,
    ),
    "workflows/sdxl-editing/sdxl-img2img.json": (
        "Replace the car with a Mitsubishi Lancer Evolution VIII in Evo Blue Pearl, same lighting",
        SDXL_NEG,
    ),
    "workflows/sdxl-editing/sdxl-inpaint.json": (
        "Fill the masked region with matching asphalt texture and lane markings",
        SDXL_NEG,
    ),
    "workflows/sdxl-editing/sdxl-outpaint.json": (
        "Extend the scene with more city street and neon signs, consistent perspective",
        SDXL_NEG,
    ),
}


def get_graphs(doc: dict):
    graphs = [{"nodes": doc.get("nodes", []), "links": doc.get("links", [])}]
    definitions = doc.get("definitions", {})
    for subgraph in definitions.get("subgraphs", []):
        graphs.append({"nodes": subgraph.get("nodes", []), "links": subgraph.get("links", [])})
    return graphs


def set_widget_text(node: dict, text: str):
    values = node.get("widgets_values")
    if isinstance(values, list) and values:
        values[0] = text
        return True
    return False


def link_index(links):
    by_src = {}
    for link in links:
        if not isinstance(link, list) or len(link) < 5:
            continue
        src_id = link[1]
        src_slot = link[2]
        by_src.setdefault((src_id, src_slot), []).append(link)
    return by_src


def update_file(path: Path, positive: str, negative: str):
    with path.open("r", encoding="utf-8") as f:
        doc = json.load(f)

    changed = False
    pos_count = 0
    neg_count = 0
    fallback_count = 0

    rel = path.as_posix()
    is_flux = "flux" in rel.lower() and "sdxl" not in rel.lower()
    is_ace = "ace-step" in rel

    for graph in get_graphs(doc):
        nodes = graph["nodes"]
        links = graph["links"]
        nodes_by_id = {n.get("id"): n for n in nodes}
        by_src = link_index(links)

        for node in nodes:
            node_type = node.get("type", "")

            if node_type == "CLIPTextEncode":
                outgoing = by_src.get((node.get("id"), 0), [])
                role = None
                for link in outgoing:
                    dst_node = nodes_by_id.get(link[3], {})
                    dst_type = dst_node.get("type", "")
                    dst_slot = link[4]
                    if dst_type in ("KSampler", "KSamplerAdvanced"):
                        if dst_slot == 1:
                            role = "positive"
                            break
                        if dst_slot == 2:
                            role = "negative"
                            break

                if role == "positive":
                    if set_widget_text(node, positive):
                        changed = True
                        pos_count += 1
                elif role == "negative":
                    neg_value = "" if is_flux else negative
                    if set_widget_text(node, neg_value):
                        changed = True
                        neg_count += 1
                else:
                    # Fallback for wrapped/subgraph flows where role can't be inferred.
                    if set_widget_text(node, positive):
                        changed = True
                        fallback_count += 1

            elif node_type == "PrimitiveStringMultiline":
                if set_widget_text(node, positive):
                    changed = True
                    pos_count += 1
            elif node_type == "TextEncodeAceStepAudio1.5":
                if set_widget_text(node, positive):
                    changed = True
                    pos_count += 1
            else:
                # Wrapper/subgraph nodes with proxied "text" widget in widgets_values[0].
                proxy = node.get("properties", {}).get("proxyWidgets")
                values = node.get("widgets_values")
                has_text_proxy = isinstance(proxy, list) and any(
                    isinstance(p, list) and len(p) >= 2 and p[1] == "text" for p in proxy
                )
                if has_text_proxy and isinstance(values, list) and values and isinstance(values[0], str):
                    if set_widget_text(node, positive):
                        changed = True
                        pos_count += 1

    if changed:
        with path.open("w", encoding="utf-8", newline="\n") as f:
            json.dump(doc, f, indent=2, ensure_ascii=False)
            f.write("\n")

    if is_ace:
        print(f"[OK] {rel}: positive prompt set ({len(positive)} chars), negative prompt set (n/a)")
    else:
        print(f"[OK] {rel}: positive prompt set ({len(positive)} chars), negative prompt set")

    return changed, pos_count, neg_count, fallback_count


def pack_name(rel_path: str):
    if "workflow-flux2-klein" in rel_path or "flux2/" in rel_path:
        return "flux2"
    if "sdxl-lightning/" in rel_path:
        return "sdxl-lightning"
    if "flux1-krea/" in rel_path:
        return "flux1-krea"
    if "newbie-image/" in rel_path:
        return "newbie-image"
    if "ovis-image/" in rel_path:
        return "ovis-image"
    if "wan-2-2/" in rel_path:
        return "wan-2-2"
    if "ace-step/" in rel_path:
        return "ace-step"
    if "hunyuan-3d/" in rel_path:
        return "hunyuan-3d"
    if "z-anime/" in rel_path:
        return "z-image-anime"
    if "ernie-image/" in rel_path:
        return "ernie-image"
    if "firered-image-edit/" in rel_path:
        return "firered-image-edit"
    return "other"


def safe_console(text: str):
    return text.encode("cp1252", errors="replace").decode("cp1252")


def main():
    root = Path("workflows")
    files = sorted(
        p.as_posix()
        for p in root.rglob("*.json")
        if "/_templates/" not in p.as_posix()
    )
    missing = [f for f in files if f not in SCENES]
    if missing:
        raise RuntimeError(f"Scene mapping missing for files: {missing}")

    verification = {}
    for rel in files:
        pos, neg = SCENES[rel]
        changed, pos_count, neg_count, fallback_count = update_file(Path(rel), pos, neg)
        pack = pack_name(rel)
        if pack not in verification:
            verification[pack] = {
                "file": rel,
                "positive": pos,
                "negative": neg,
                "changed": changed,
                "pos_count": pos_count,
                "neg_count": neg_count,
                "fallback_count": fallback_count,
            }

    print("\n[VERIFY] One workflow per pack:")
    for pack in sorted(verification):
        info = verification[pack]
        print(f"  pack={pack} file={info['file']}")
        print(f"    positive: {safe_console(info['positive'])}")
        neg = info["negative"] if info["negative"] else "<empty>"
        print(f"    negative: {safe_console(neg)}")
        print(
            f"    counts: changed={info['changed']}, pos_nodes={info['pos_count']}, "
            f"neg_nodes={info['neg_count']}, fallback_nodes={info['fallback_count']}"
        )


if __name__ == "__main__":
    main()
