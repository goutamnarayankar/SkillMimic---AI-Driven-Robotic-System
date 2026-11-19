
import json
import sys
from pathlib import Path

import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.callbacks import (
    ModelCheckpoint,
    EarlyStopping,
    ReduceLROnPlateau
)


# -----------------------------------------
# PROJECT PATHS
# -----------------------------------------

ROOT = Path(__file__).resolve().parents[1]

DATASET_DIR = ROOT / "data" / "dataset"
MODEL_DIR = ROOT / "data" / "models"

MODEL_DIR.mkdir(parents=True, exist_ok=True)

IMAGE_SIZE = (160, 160)
BATCH_SIZE = 32
EPOCHS = 30
SEED = 42

EXPECTED_CLASSES = [
    "Closed",
    "Grasp",
    "Grasp_down",
    "Open",
    "Pinch",
    "Writing"
]


# -----------------------------------------
# DATASET VALIDATION
# -----------------------------------------

def validate_dataset():

    if not DATASET_DIR.exists():
        raise FileNotFoundError(
            f"Dataset directory not found: {DATASET_DIR}"
        )

    actual_classes = sorted(
        folder.name
        for folder in DATASET_DIR.iterdir()
        if folder.is_dir()
    )

    if actual_classes != EXPECTED_CLASSES:
        raise ValueError(
            "Dataset folders do not match the expected classes.\n"
            f"Expected: {EXPECTED_CLASSES}\n"
            f"Found: {actual_classes}"
        )

    for class_name in EXPECTED_CLASSES:

        image_count = sum(
            1
            for path in (DATASET_DIR / class_name).iterdir()
            if path.is_file()
            and path.suffix.lower() in {
                ".jpg", ".jpeg", ".png", ".bmp", ".webp"
            }
        )

        if image_count == 0:
            raise ValueError(
                f"No images found in {class_name}"
            )

        print(f"{class_name}: {image_count} images")


# -----------------------------------------
# LOAD DATASET
# -----------------------------------------

def load_dataset():

    train_dataset = (
        tf.keras.utils.image_dataset_from_directory(
            DATASET_DIR,
            labels="inferred",
            label_mode="int",
            class_names=EXPECTED_CLASSES,
            image_size=IMAGE_SIZE,
            batch_size=BATCH_SIZE,
            validation_split=0.2,
            subset="training",
            seed=SEED,
            color_mode="rgb",
            shuffle=True
        )
    )

    validation_dataset = (
        tf.keras.utils.image_dataset_from_directory(
            DATASET_DIR,
            labels="inferred",
            label_mode="int",
            class_names=EXPECTED_CLASSES,
            image_size=IMAGE_SIZE,
            batch_size=BATCH_SIZE,
            validation_split=0.2,
            subset="validation",
            seed=SEED,
            color_mode="rgb",
            shuffle=False
        )
    )

    # Preserve the previous project's raw 0-255
    # float32 image input convention.
    train_dataset = train_dataset.map(
        lambda images, labels: (
            tf.cast(images, tf.float32),
            labels
        )
    )

    validation_dataset = validation_dataset.map(
        lambda images, labels: (
            tf.cast(images, tf.float32),
            labels
        )
    )

    return train_dataset, validation_dataset


# -----------------------------------------
# BUILD MOBILENETV2 MODEL
# -----------------------------------------

def build_model():

    base_model = MobileNetV2(
        input_shape=(160, 160, 3),
        include_top=False,
        weights="imagenet"
    )

    base_model.trainable = False

    inputs = layers.Input(
        shape=(160, 160, 3)
    )

    features = base_model(
        inputs,
        training=False
    )

    features = layers.GlobalAveragePooling2D()(
        features
    )

    features = layers.Dense(
        128,
        activation="relu"
    )(features)

    features = layers.Dropout(0.3)(
        features
    )

    outputs = layers.Dense(
        6,
        activation="softmax"
    )(features)

    model = models.Model(
        inputs=inputs,
        outputs=outputs
    )

    model.compile(
        optimizer=tf.keras.optimizers.Adam(),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"]
    )

    return model


# -----------------------------------------
# TRAINING
# -----------------------------------------

def train_model():

    print("\nSKILLMIMIC GESTURE MODEL TRAINING")
    print("=" * 45)

    validate_dataset()

    train_data, validation_data = load_dataset()

    model = build_model()

    model.summary()

    best_model_path = (
        MODEL_DIR / "best_fast_gesture.h5"
    )

    final_model_path = (
        MODEL_DIR / "fast_gesture_model.h5"
    )

    callbacks = [

        ModelCheckpoint(
            filepath=str(best_model_path),
            monitor="val_accuracy",
            save_best_only=True,
            mode="max",
            verbose=1
        ),

        EarlyStopping(
            monitor="val_loss",
            patience=6,
            restore_best_weights=True,
            verbose=1
        ),

        ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=3,
            min_lr=1e-6,
            verbose=1
        )
    ]

    history = model.fit(
        train_data,
        validation_data=validation_data,
        epochs=EPOCHS,
        callbacks=callbacks
    )

    model.save(final_model_path)

    labels_path = MODEL_DIR / "gesture_labels.json"

    with open(
        labels_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            {
                "class_names": EXPECTED_CLASSES,
                "input_size": list(IMAGE_SIZE),
                "input_color": "RGB",
                "input_scale": "0_to_255"
            },
            file,
            indent=4
        )

    print("\nTRAINING COMPLETED")
    print(f"Best model: {best_model_path}")
    print(f"Final model: {final_model_path}")
    print(f"Labels: {labels_path}")

    return history


if __name__ == "__main__":

    try:
        train_model()

    except Exception as error:
        print(f"\nTraining error: {error}")
        sys.exit(1)
