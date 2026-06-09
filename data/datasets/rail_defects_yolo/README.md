# Rail Defects YOLO Dataset

This directory is the reserved YOLO dataset layout for training `data/models/rail_defects.pt`.

```text
data/datasets/rail_defects_yolo
  data.yaml
  images/
    train/
    val/
    test/
  labels/
    train/
    val/
    test/
```

Label format follows standard YOLO detection labels:

```text
class_id x_center y_center width height
```

Coordinates must be normalized to `[0, 1]`. `class_id` must match `data.yaml` and `rail_inspection_perception.fault_catalog.FAULT_CLASSES`.

The actual images and labels are ignored by Git. Keep only this structure and metadata in the repository.

Check the dataset structure:

```powershell
python .\scripts\dataset_check.py
```

Train later with Ultralytics inside the project container:

```bash
yolo detect train data=/workspace/data/datasets/rail_defects_yolo/data.yaml model=yolov8n.pt imgsz=640 epochs=100
```
