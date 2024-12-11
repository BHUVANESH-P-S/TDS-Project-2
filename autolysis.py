#import required libraries
import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import openai
from pathlib import Path
import requests

#function to load api key from environment variable
def initialize_openai():
    openai.api_key = os.getenv('AIPROXY_TOKEN')
    if not openai.api_key:
        raise EnvironmentError("AIPROXY_TOKEN environment variable not set.")

# function to Load dataset
def load_dataset(file_path):
    try:
        # Attempt to read the file with UTF-8 encoding
        df = pd.read_csv(file_path, encoding='utf-8')
        return df
    except UnicodeDecodeError:
        # If UTF-8 fails, try with a fallback encoding
        df = pd.read_csv(file_path, encoding='latin1')
        return df
    except Exception as e:
        #Exception handling for FileNotFoundError
        raise FileNotFoundError(f"Error loading file {file_path}: {e}")

# Function to Perform basic analysis
def basic_analysis(df):
    summary = df.describe(include='all')
    missing_values = df.isnull().sum()
    column_types = df.dtypes
    df_info=df.info()

    # Generate basic insights
    insights = {
        "Summary": summary,
        "Missing_values": missing_values,
        "Column_types": column_types,
        "Dataset info": df_info
    }

    return insights

#Function to Generate visualizations like Histogram and Correlation Heatmap
def generate_visualizations(df):
    charts = []
    
    # Correlation heatmap for numerical columns
    numerical_df = df.select_dtypes(include='number')  # Select only numerical columns
    if not numerical_df.empty:
        plt.figure(figsize=(10, 8))
        corr = numerical_df.corr()  # Calculate correlation on numerical data
        sns.heatmap(corr, annot=True, cmap='coolwarm', fmt='.2f')
        heatmap_path = "correlation_heatmap.png"
        plt.savefig(heatmap_path)
        plt.close()
        with Image.open(heatmap_path) as img:
            img = img.resize((512, 512))
            img.save(heatmap_path) 
        charts.append(str(heatmap_path))

    # Histogram for numerical columns
    for col in numerical_df.columns:  # Iterate through numerical columns
        plt.figure(figsize=(10, 8))
        sns.histplot(df[col].dropna(), kde=True, bins=30)
        hist_path = f"histogram_{col}.png"
        plt.savefig(hist_path)
        plt.close()
        with Image.open(hist_path) as img:
            img = img.resize((512, 512))
            img.save(hist_path)
        charts.append(str(hist_path))

    return charts

# Function to Generate narrative using LLM
def generate_narrative(insights, images):
    prompt = f"""
    Dataset Analysis Report:
    Dataset Summary: {insights['Summary']}
    Missing Values: {insights['Missing_values']}
    Column Types: {insights['Column_types']}
    Dataset Info: {insights['Dataset info']}

    Please provide a detailed narrative of the dataset, covering the following points:  

    1. Dataset Overview: Briefly describe the dataset, including its purpose, structure, and variable types.  
    2. Exploratory Analysis: Summarize methods used and note data quality issues (e.g., missing values, outliers, duplicates).  
    3. Feature Relationships: Highlight correlations, patterns, clusters, and unexpected relationships between variables.  
    4. Key Insights: Outline significant findings, trends, and drivers affecting key variables.  
    5. Implications: Discuss the relevance of findings, suggest improvements, and recommend actionable steps.  
    6. Visualizations:  Include relevant charts to support insights and briefly explain their significance.  
    7. Hypotheses: Propose questions or hypotheses for further analysis based on the findings.  
    """

    # Send the request to the custom API
    response = requests.post(
        "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {openai.api_key}"},
        json={
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a data analyst."},
                {"role": "user", "content": prompt}
            ]
        }
    )

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"].strip()
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return None

# Write results to README.md
def write_readme(narrative, charts):
    readme_path = "README.md"
    with open(readme_path, "w") as f:
        f.write("# Automated Data Analysis\n\n")
        if narrative:
            f.write(narrative + "\n\n")
        else:
            f.write("Error generating narrative.\n\n")
        for chart in charts:
            f.write(f"![Chart]({chart})\n")

# Main function
def main(file_path):
    # Initialize and load dataset
    initialize_openai()
    df = load_dataset(file_path)

    # Perform analysis
    summary = basic_analysis(df)
    charts = generate_visualizations(df)
    narrative = generate_narrative(summary, charts)

    # Write results
    write_readme(narrative, charts)
    print("Analysis complete. Results saved")
    print("Download your results using the following link:")
    print("[Download README.md](./output/README.md)")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: uv run autolysis.py <dataset.csv>")
    else:
        dataset_file = sys.argv[1]
        main(file_path)
