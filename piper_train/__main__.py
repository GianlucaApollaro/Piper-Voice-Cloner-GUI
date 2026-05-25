import argparse
import json
import logging
import torch

# Optimize for Tensor Cores (RTX 30/40/50 series)
# Wrap in try-except to ensure portability with older hardware/PyTorch versions
try:
    torch.set_float32_matmul_precision('medium')
except (AttributeError, RuntimeError):
    pass

from pathlib import Path

import torch
from pytorch_lightning import Trainer
from pytorch_lightning import Trainer
from pytorch_lightning.callbacks import ModelCheckpoint, Callback
from pytorch_lightning.loggers import TensorBoardLogger, CSVLogger

class PrintingCallback(Callback):
    def on_train_batch_end(self, trainer, pl_module, outputs, batch, batch_idx):
        # Print loss every N steps to avoid spamming, but ensure it's visible
        # Check if we have loss
        if trainer.global_step % 10 == 0:
            loss = trainer.callback_metrics.get("loss") or trainer.callback_metrics.get("train/loss") or trainer.callback_metrics.get("total_loss")
            if loss is not None:
                # Use _LOGGER to skip stdout buffering issues
                _LOGGER.info(f"loss={loss.item():.4f}")

    def on_validation_end(self, trainer, pl_module):
         val_loss = trainer.callback_metrics.get("val_loss")
         if val_loss is not None:
             _LOGGER.info(f"val_loss={val_loss.item():.4f}")

from .vits.lightning import VitsModel

_LOGGER = logging.getLogger(__package__)


def main():
    print("--- [VERIFICA BUILD]: CODICE AGGIORNATO CON CSV LOGGER E PRINTING FIX ---", flush=True)
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset-dir", required=True, help="Path to pre-processed dataset directory"
    )
    parser.add_argument(
        "--dataset-config", help="Path to dataset.jsonl (defaults to dataset_dir/dataset.jsonl)"
    )
    parser.add_argument(
        "--checkpoint-epochs",
        type=int,
        help="Save checkpoint every N epochs (default: 1)",
    )
    parser.add_argument(
        "--quality",
        default="medium",
        choices=("x-low", "medium", "high"),
        help="Quality/size of model (default: medium)",
    )
    parser.add_argument(
        "--resume_from_single_speaker_checkpoint",
        help="For multi-speaker models only. Converts a single-speaker checkpoint to multi-speaker and resumes training",
    )
    Trainer.add_argparse_args(parser)
    VitsModel.add_model_specific_args(parser)
    parser.add_argument("--seed", type=int, default=1234)
    args = parser.parse_args()
    _LOGGER.debug(args)

    args.dataset_dir = Path(args.dataset_dir)
    if not args.default_root_dir:
        args.default_root_dir = args.dataset_dir

    torch.backends.cudnn.benchmark = True
    torch.manual_seed(args.seed)

    config_path = args.dataset_dir / "config.json"
    if args.dataset_config:
        dataset_path = Path(args.dataset_config)
    else:
        dataset_path = args.dataset_dir / "dataset.jsonl"

    with open(config_path, "r", encoding="utf-8") as config_file:
        # See preprocess.py for format
        config = json.load(config_file)
        num_symbols = int(config["num_symbols"])
        num_speakers = int(config["num_speakers"])
        sample_rate = int(config["audio"]["sample_rate"])

    # Determine version for logging to keep metrics and checkpoints aligned
    version = None
    log_dir = args.dataset_dir / "lightning_logs"
    
    existing_versions = []
    if log_dir.exists():
        for d in log_dir.iterdir():
            if d.is_dir() and d.name.startswith("version_"):
                try:
                    v = int(d.name.split("_")[1])
                    existing_versions.append(v)
                except ValueError:
                    pass
                    
    if args.resume_from_checkpoint and existing_versions:
        # If resuming, latch onto the latest existing version directory
        version = max(existing_versions)
        _LOGGER.info(f"Resuming logging into version_{version}")
    else:
        # New run: Calculate next version manually to ensure BOTH loggers use the SAME one
        if existing_versions:
            version = max(existing_versions) + 1
        else:
            version = 0
            
    _LOGGER.info(f"Setting unified logger version: {version}")

    # Create Loggers with EXPLICIT version
    csv_logger = CSVLogger(args.dataset_dir, name="lightning_logs", version=version)
    tb_logger = TensorBoardLogger(args.dataset_dir, name="lightning_logs", version=version)
    # Extract resume path and clear it from args so Trainer doesn't auto-restore 
    # using the deprecated mechanism which confuses logger versions
    resume_ckpt_path = args.resume_from_checkpoint
    if resume_ckpt_path:
        args.resume_from_checkpoint = None

    trainer = Trainer.from_argparse_args(args, logger=[tb_logger, csv_logger], default_root_dir=args.default_root_dir)
    if args.checkpoint_epochs is not None:
        # Explicitly set dirpath to ensure checkpoints go to the same place as logs
        ckpt_dirpath = None
        if version is not None:
             ckpt_dirpath = args.dataset_dir / "lightning_logs" / f"version_{version}" / "checkpoints"
             
        trainer.callbacks = [
            ModelCheckpoint(dirpath=ckpt_dirpath, every_n_epochs=args.checkpoint_epochs),
            PrintingCallback() # Add our custom logger
        ]
        _LOGGER.debug(
            "Checkpoints will be saved every %s epoch(s) to %s", args.checkpoint_epochs, ckpt_dirpath or "default location"
        )

    dict_args = vars(args)
    if args.quality == "x-low":
        dict_args["hidden_channels"] = 96
        dict_args["inter_channels"] = 96
        dict_args["filter_channels"] = 384
    elif args.quality == "high":
        dict_args["resblock"] = "1"
        dict_args["resblock_kernel_sizes"] = (3, 7, 11)
        dict_args["resblock_dilation_sizes"] = (
            (1, 3, 5),
            (1, 3, 5),
            (1, 3, 5),
        )
        dict_args["upsample_rates"] = (8, 8, 2, 2)
        dict_args["upsample_initial_channel"] = 512
        dict_args["upsample_kernel_sizes"] = (16, 16, 4, 4)

    model = VitsModel(
        num_symbols=num_symbols,
        num_speakers=num_speakers,
        sample_rate=sample_rate,
        dataset=[dataset_path],
        **dict_args,
    )

    if args.resume_from_single_speaker_checkpoint:
        assert (
            num_speakers > 1
        ), "--resume_from_single_speaker_checkpoint is only for multi-speaker models. Use --resume_from_checkpoint for single-speaker models."

        # Load single-speaker checkpoint
        _LOGGER.debug(
            "Resuming from single-speaker checkpoint: %s",
            args.resume_from_single_speaker_checkpoint,
        )
        model_single = VitsModel.load_from_checkpoint(
            args.resume_from_single_speaker_checkpoint,
            dataset=None,
        )
        g_dict = model_single.model_g.state_dict()
        for key in list(g_dict.keys()):
            # Remove keys that can't be copied over due to missing speaker embedding
            if (
                key.startswith("dec.cond")
                or key.startswith("dp.cond")
                or ("enc.cond_layer" in key)
            ):
                g_dict.pop(key, None)

        # Copy over the multi-speaker model, excluding keys related to the
        # speaker embedding (which is missing from the single-speaker model).
        load_state_dict(model.model_g, g_dict)
        load_state_dict(model.model_d, model_single.model_d.state_dict())
        _LOGGER.info(
            "Successfully converted single-speaker checkpoint to multi-speaker"
        )

    trainer.fit(model, ckpt_path=resume_ckpt_path)


def load_state_dict(model, saved_state_dict):
    state_dict = model.state_dict()
    new_state_dict = {}

    for k, v in state_dict.items():
        if k in saved_state_dict:
            # Use saved value
            new_state_dict[k] = saved_state_dict[k]
        else:
            # Use initialized value
            _LOGGER.debug("%s is not in the checkpoint", k)
            new_state_dict[k] = v

    model.load_state_dict(new_state_dict)


# -----------------------------------------------------------------------------


if __name__ == "__main__":
    main()
