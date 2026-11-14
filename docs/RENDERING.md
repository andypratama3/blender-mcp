# Rendering

Rendering is **off by default**. This kit verifies with numbers, not pixels, and never
starts a render just to look at the result. Read this page only when the owner has
explicitly asked for an image, a preview, or a video.

## 1. When rendering is allowed

Allowed:

- The owner says "render", "preview", "show me a picture", "make a turntable".
- A deliverable explicitly requires an image (thumbnail, store shot, client preview).

Not allowed:

- As verification of a rig, mesh, or transform.
- To "check if it looks right" while working.
- On your own initiative after finishing a task.
- As a substitute for reported numbers.

If you think a render would help but nobody asked, ask first and wait.

## 2. Pick the engine from the enum

Blender 5.4 renamed EEVEE. Hardcoding the old name raises `enum "BLENDER_EEVEE_NEXT"
not found`. Always read the enum:

```python
engines = [
    item.identifier
    for item in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items
]
engine = next(
    name for name in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT") if name in engines
)
scene.render.engine = engine
```

## 3. glTF scenes have no camera and no lights

An imported glTF ships geometry, materials, and often animation — but no camera and no
light. A render without setup produces a black frame. Create both in a collection named
`Render_Setup` so they are easy to delete later:

```python
import bpy, math

scene = bpy.context.scene
setup = bpy.data.collections.get("Render_Setup") or bpy.data.collections.new("Render_Setup")
if setup.name not in scene.collection.children:
    scene.collection.children.link(setup)

def link(ob):
    setup.objects.link(ob)
    return ob

if scene.camera is None:
    cam_data = bpy.data.cameras.new("Preview_Cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = 1.0
    cam = link(bpy.data.objects.new("Preview_Cam", cam_data))
    cam.location = (0.0, -2.0, -0.055)
    cam.rotation_euler = (math.radians(90), 0.0, 0.0)
    scene.camera = cam

if not any(o.type == "LIGHT" for o in scene.objects):
    key = bpy.data.lights.new("Preview_Key", "AREA")
    key.energy = 300
    key.size = 2.0
    light = link(bpy.data.objects.new("Preview_Key", key))
    light.location = (1.5, -2.0, 1.5)
    light.rotation_euler = (math.radians(55), 0.0, math.radians(35))
```

Use `ORTHO` for flat mechanical assets: it keeps proportions readable and avoids
perspective distortion on a tool that is 0.4 m tall.

## 4. Render one still

```python
import os

scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.render.filepath = "/abs/project/render/preview.png"

bpy.ops.render.render(write_still=True)
result = {
    "image": scene.render.filepath,
    "bytes": os.path.getsize(scene.render.filepath),
    "engine": scene.render.engine,
    "camera": scene.camera.name,
}
```

Rules:

- Save the `.blend` before rendering.
- Write inside `<project>/render/`, never into the repo.
- Report the absolute path and file size.
- Raise the client timeout: `--timeout 1800`.
- Do not start a headless render of a file with unsaved changes.

## 5. Video or turntable

```python
scene.frame_start, scene.frame_end = 1, 60
scene.render.fps = 24
scene.render.image_settings.file_format = "FFMPEG"
scene.render.ffmpeg.format = "MPEG4"
scene.render.ffmpeg.codec = "H264"
scene.render.ffmpeg.constant_rate_factor = "HIGH"
scene.render.filepath = "/abs/project/render/preview.mp4"
bpy.ops.render.render(animation=True)
```

For a turntable, keyframe the camera's `rotation_euler.z` over the frame range; do not
rotate the asset, or you invalidate the rest pose you just verified.

## 6. Geometry nodes, drivers, and modifiers in renders

- Drivers evaluate automatically during render; there is no need to call `frame_set`.
- The render uses the evaluated depsgraph, so armature deformation, modifiers, and
  constraints are all applied.
- If a render looks different from your measurements, the mismatch is in the setup
  (hidden objects, collection exclusion, wrong frame), not in the numbers.

## 7. Cost and time

| Setting | Still | Animation |
|---|---|---|
| EEVEE, 1080p | seconds | fast |
| Cycles, 1080p, 128 samples | minutes | slow |
| 4K Cycles | long | only with a clear reason |

Prefer EEVEE unless the owner asks for Cycles quality or the material needs it (glass,
volumetrics, caustics). Always state which engine and resolution you used.

## 8. Cleanup

After a render that was only a preview:

1. Keep `Render_Setup` if the owner may want another render.
2. Remove it if they asked for a clean scene.
3. Do not save the `.blend` with an unsaved render path pointing at a temp file.
