import pandas as pd
import os
import matplotlib
matplotlib.use('Agg') # Force non-interactive backend
import matplotlib.pyplot as plt

def analyze_training_metrics(metrics_path, dataset_path):
    """
    Analyzes the metrics.csv file and generates a report.
    """
    try:
        df = pd.read_csv(metrics_path)
    except Exception as e:
        return f"Error reading CSV: {e}"

    # Remove rows where loss_gen_all is NaN (if any)
    if 'loss_gen_all' in df.columns:
        df = df.dropna(subset=['loss_gen_all'])
    else:
        return "Error: 'loss_gen_all' column not found in metrics.csv."

    # Basic Stats
    total_steps = len(df)
    if total_steps == 0:
        return "No data points found."

    initial_loss = df['loss_gen_all'].iloc[0]
    final_loss = df['loss_gen_all'].iloc[-1]
    min_loss = df['loss_gen_all'].min()
    
    # Dynamic Window Calculation: Last 10% or minimum 100 steps
    window_pct = 0.10
    dynamic_window_size = max(100, int(total_steps * window_pct))
    
    # Ensure ignore window doesn't exceed total steps
    if dynamic_window_size > total_steps:
        dynamic_window_size = total_steps

    last_n_steps = df.tail(dynamic_window_size)
    
    # Calculate convergence rate (rolling average change)
    # We smooth it out to see trend
    df['loss_smooth'] = df['loss_gen_all'].rolling(window=20).mean()
    
    # Stability: Standard Deviation of the dynamic window
    stability_std = last_n_steps['loss_gen_all'].std()
    
    # Anomaly Detection: Spikes > 50% increase from smoothed loss
    # We use a simple heuristic: if raw loss > 1.5 * smoothed loss
    anomalies = df[df['loss_gen_all'] > (df['loss_smooth'] * 1.5)]
    num_anomalies = len(anomalies)

    # Quality Report String
    report = []
    report.append("=== PIPER TRAINING ANALYSIS REPORT ===")
    report.append(f"Analyzed File: {metrics_path}")
    report.append(f"Total Steps Logged: {total_steps}")
    report.append(f"Analysis Window: Last {dynamic_window_size} steps")
    report.append("")
    report.append("--- LOSS STATS ---")
    report.append(f"Initial Loss: {initial_loss:.4f}")
    report.append(f"Final Loss:   {final_loss:.4f}")
    report.append(f"Minimum Loss: {min_loss:.4f}")
    report.append(f"Loss Delta:   {final_loss - initial_loss:.4f} (Negative is good)")
    report.append("")
    
    report.append("--- STABILITY & QUALITY ---")
    
    # Estimate Quality based on final loss threshold
    # These thresholds are heuristics and might need tuning for different datasets
    if final_loss < 35.0:
        quality_est = "EXCELLENT"
    elif final_loss < 40.0:
        quality_est = "GOOD"
    elif final_loss < 45.0:
        quality_est = "FAIR"
    else:
        quality_est = "POOR / UNDERFITTING"
        
    report.append(f"Estimated Quality: {quality_est}")
    report.append(f"Stability (StdDev in window): {stability_std:.4f}")
    
    if stability_std < 0.5:
        report.append("Status: STABLE (Converged or close to convergence)")
    elif stability_std < 2.0:
        report.append("Status: FLUCTUATING (Still training or noisy)")
    else:
        report.append("Status: UNSTABLE (High variance, check learning rate)")

    report.append("")
    report.append("--- ANOMALIES ---")
    if num_anomalies > 0:
        report.append(f"WARNING: Detected {num_anomalies} loss spikes (>50% above trend).")
        report.append("Check your dataset for bad audio segments or silence.")
    else:
        report.append("No significant loss spikes detected.")
        
    final_report_text = "\n".join(report)
    
    # Save Report
    output_txt = os.path.join(dataset_path, "analysis_report.txt")
    with open(output_txt, "w", encoding="utf-8") as f:
        f.write(final_report_text)
        
    # Generate Plot
    try:
        plt.figure(figsize=(10, 6))
        plt.plot(df['step'], df['loss_gen_all'], label='Total Generator Loss', alpha=0.3)
        plt.plot(df['step'], df['loss_smooth'], label='Smoothed Loss (MA-20)', color='red')
        
        # Highlight Analysis Window
        window_start_step = last_n_steps['step'].iloc[0]
        plt.axvline(x=window_start_step, color='orange', linestyle='--', label='Analysis Start')

        # Add Disc Loss if available
        if 'loss_disc_all' in df.columns:
            plt.plot(df['step'], df['loss_disc_all'], label='Discriminator Loss', alpha=0.3, color='green')

        plt.title('Training Loss Convergence')
        plt.xlabel('Steps')
        plt.ylabel('Loss')
        plt.legend()
        plt.grid(True)
        
        plot_path = os.path.join(dataset_path, "loss_plot.png")
        plt.savefig(plot_path)
        plt.close()
        final_report_text += f"\n\n[Plot Saved]: {plot_path}"
    except Exception as e:
        final_report_text += f"\n\n[Plot Error]: Could not generate plot ({e})"

    return final_report_text

if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze Piper Training Metrics')
    parser.add_argument('--input', help='Path to metrics.csv', default='dummy_metrics.csv')
    parser.add_argument('--dataset', help='Path to dataset/output folder', default='.')
    
    args = parser.parse_args()
    
    # If input is just a filename, assume it might be relative
    if not os.path.exists(args.input):
        print(f"Error: Input file {args.input} not found.")
    else:
        print(f"Analyzing {args.input}...")
        report = analyze_training_metrics(args.input, args.dataset)
        print(report)
