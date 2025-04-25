import os
import json
import logging
import pandas as pd
from tqdm import tqdm
import argparse
from typing import Dict, List, Tuple

from graph import WikidataQueryAgent
from tools.sparql_tool import WikidataSPARQLTool

# Set up logger
logger = logging.getLogger(__name__)

def compare_two_dataframes(df1: pd.DataFrame, df2: pd.DataFrame) -> Dict[str, float]:
    """
    Compare two dataframes and calculate various metrics.
    df1: DataFrame for ground truth
    df2: DataFrame for predicted
    """
    logger.info(f"Comparing dataframes: ground truth shape {df1.shape}, predicted shape {df2.shape}")
    
    if len(df1.columns) != len(df2.columns):
        logger.warning(f"Column count mismatch: ground truth {len(df1.columns)}, predicted {len(df2.columns)}")
        return {
            'jaccard': 0,
            'recall': 0,
            'precision': 0,
            'f1': 0,
            'tp': 0,
            'fp': 0,
            'fn': 0,
            'tn': 0
        }

    set1, set2 = set(), set()
    for _, row in df1.iterrows():
        row = list(row)
        row = sorted(row)
        row = tuple(row)
        set1.add(row)

    for _, row in df2.iterrows():
        row = list(row)
        row = sorted(row)
        row = tuple(row)
        set2.add(row)
    
    logger.debug(f"Converted to sets: ground truth {len(set1)} unique rows, predicted {len(set2)} unique rows")
    
    jaccard = len(set1 & set2) / len(set1 | set2) if len(set1 | set2) > 0 else 0
    # recall = correct retrieved / all ground truth
    recall = len(set1 & set2) / len(set1) if len(set1) > 0 else 0
    # precision = correct retrieved / retrieved answers
    precision = len(set1 & set2) / len(set2) if len(set2) > 0 else 0
    # f1 score = 2 x prec x recall / (prec + recall)
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    # TP, TN, FP, FN computation (might be useful for computing micro metrics)
    tp = len(set1 & set2)
    fp = len(set2) - tp
    fn = len(set1) - tp
    total_pairs = len(set1) + len(set2) - tp
    tn = total_pairs - (tp + fp + fn)

    metrics = {
        'jaccard': jaccard,
        'recall': recall,
        'precision': precision,
        'f1': f1,
        'tp': tp,
        'fp': fp,
        'fn': fn,
        'tn': tn
    }
    
    logger.info(f"Metrics: jaccard={jaccard:.4f}, precision={precision:.4f}, recall={recall:.4f}, f1={f1:.4f}")
    logger.debug(f"Detailed metrics: tp={tp}, fp={fp}, fn={fn}, tn={tn}")
    
    return metrics

def execute_sparql_to_df(query: str) -> pd.DataFrame:
    """Execute a SPARQL query and convert results to DataFrame"""
    logger.info(f"Executing SPARQL query to DataFrame")
    logger.debug(f"Query: {query}")
    
    sparql_tool = WikidataSPARQLTool()
    result = sparql_tool.execute(query)
    
    if result.get('success', False) and 'results' in result:
        # Convert results to DataFrame
        df = pd.DataFrame(result['results'])
        logger.info(f"Query execution successful: {df.shape[0]} rows, {df.shape[1]} columns")
        return df
    else:
        # Return empty DataFrame on error
        error = result.get('error', 'Unknown error')
        logger.error(f"Query execution failed: {error}")
        return pd.DataFrame()

def evaluate_wikidata_agent(agent: WikidataQueryAgent, test_data_path: str, output_log_path: str = "evaluation_results.json"):
    """Evaluate the Wikidata Agent against a test dataset"""
    
    # Load test data
    logger.info(f"Loading test data from {test_data_path}")
    with open(test_data_path, 'r') as f:
        test_data = json.load(f)
    
    logger.info(f"Loaded {len(test_data)} test items")
    
    # For testing, limit to first few examples
    test_data = test_data[:3]
    logger.info(f"Using first {len(test_data)} test items for evaluation")
    
    # Prepare results storage
    results = []
    metrics_sum = {
        'jaccard': 0,
        'recall': 0,
        'precision': 0,
        'f1': 0,
        'tp': 0,
        'fp': 0,
        'fn': 0,
        'tn': 0
    }
    
    # Process each test question
    for i, test_item in tqdm(enumerate(test_data), total=len(test_data), desc="Evaluating"):
        question = test_item['question']
        ground_truth_query = test_item['sparql']
        
        logger.info(f"Processing question {i+1}/{len(test_data)}: {question}")
        print(f"\nProcessing question {i+1}/{len(test_data)}: {question}")
        
        try:
            # Generate query using the agent
            logger.info("Generating query using agent")
            result = agent.query(question)
            generated_query = result['sparql_query']
            logger.info(f"Agent generated query: {generated_query}")
            
            # Execute both queries to get dataframes
            logger.info("Executing ground truth query...")
            ground_truth_df = execute_sparql_to_df(ground_truth_query)
            
            logger.info("Executing generated query...")
            generated_df = execute_sparql_to_df(generated_query)
            
            # Compare results
            logger.info("Comparing query results")
            metrics = compare_two_dataframes(ground_truth_df, generated_df)
            
            # Update metrics sum
            for key in metrics_sum:
                metrics_sum[key] += metrics[key]
            
            # Save individual result
            result_item = {
                'question': question,
                'ground_truth_query': ground_truth_query,
                'generated_query': generated_query,
                'metrics': metrics,
                'success': True
            }
            
            print(f"Metrics: Precision: {metrics['precision']:.4f}, Recall: {metrics['recall']:.4f}, F1: {metrics['f1']:.4f}")
            
        except Exception as e:
            logger.error(f"Error processing question: {str(e)}", exc_info=True)
            print(f"Error: {str(e)}")
            result_item = {
                'question': question,
                'ground_truth_query': ground_truth_query,
                'error': str(e),
                'success': False
            }
            
            # Add zeros to metrics for failed queries
            for key in metrics_sum:
                metrics_sum[key] += 0
        
        results.append(result_item)
        
        # Print progress and current average metrics
        if (i + 1) % 5 == 0 or i == len(test_data) - 1:
            avg_metrics = {k: v / (i + 1) for k, v in metrics_sum.items()}
            logger.info(f"Current average metrics after {i + 1}/{len(test_data)} questions:")
            logger.info(f"Precision: {avg_metrics['precision']:.4f}, Recall: {avg_metrics['recall']:.4f}, F1: {avg_metrics['f1']:.4f}")
            
            print(f"\nCurrent average metrics after {i + 1}/{len(test_data)} questions:")
            print(f"Precision: {avg_metrics['precision']:.4f}")
            print(f"Recall: {avg_metrics['recall']:.4f}")
            print(f"F1: {avg_metrics['f1']:.4f}")
            print(f"Jaccard: {avg_metrics['jaccard']:.4f}")
    
    # Calculate average metrics
    avg_metrics = {k: v / len(test_data) for k, v in metrics_sum.items()}
    logger.info(f"Final average metrics: {avg_metrics}")
    
    # Save results
    final_results = {
        'results': results,
        'average_metrics': avg_metrics
    }
    
    logger.info(f"Saving evaluation results to {output_log_path}")
    with open(output_log_path, 'w') as f:
        json.dump(final_results, f, indent=2)
    
    return final_results

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    parser = argparse.ArgumentParser(description="Evaluate Wikidata Agent on test dataset")
    parser.add_argument("--test-data", type=str, default="dataset/qald_9_plus/qald_9_plus_test_wikidata.json", 
                        help="Path to test data JSON file")
    parser.add_argument("--output", type=str, default="evaluation_results.json",
                        help="Path to output results file")
    parser.add_argument("--api-key", type=str, default=None,
                        help="Gemini API key (will use environment variable if not provided)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Enable verbose (debug) logging")
    args = parser.parse_args()
    
    # Set log level based on verbosity
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize agent
    logger.info("Initializing Wikidata Agent...")
    agent = WikidataQueryAgent(args.api_key)
    
    # Run evaluation
    logger.info(f"Evaluating agent on {args.test_data}...")
    results = evaluate_wikidata_agent(agent, args.test_data, args.output)
    
    # Print summary
    logger.info("\nEvaluation complete!")
    logger.info(f"Results saved to {args.output}")
    logger.info("\nAverage Metrics:")
    for key, value in results['average_metrics'].items():
        logger.info(f"{key}: {value:.4f}")
        print(f"{key}: {value:.4f}")