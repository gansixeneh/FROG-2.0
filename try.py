from transformers import XLNetTokenizer, XLNetModel
import torch
import torch.nn.functional as F

# Load pre-trained model and tokenizer
tokenizer = XLNetTokenizer.from_pretrained('xlnet-base-cased')
model = XLNetModel.from_pretrained('xlnet-base-cased')

def get_xlnet_embeddings(text):
    # Always use special tokens for proper model behavior
    inputs = tokenizer(text, return_tensors='pt', add_special_tokens=True)
    
    # Get model outputs
    with torch.no_grad():
        outputs = model(**inputs)
    
    # Get the last hidden states
    last_hidden_states = outputs.last_hidden_state
    
    # Use mean pooling to get a single vector representation
    # This averages all token embeddings to create a sentence embedding
    embeddings = last_hidden_states.mean(dim=1)
    
    return embeddings

def compute_similarity(question, answer):
    # Get embeddings for question and answer
    question_embedding = get_xlnet_embeddings(question)
    answer_embedding = get_xlnet_embeddings(answer)
    
    # Normalize embeddings for cosine similarity
    question_embedding = F.normalize(question_embedding, p=2, dim=1)
    answer_embedding = F.normalize(answer_embedding, p=2, dim=1)
    
    # Compute cosine similarity
    similarity = torch.matmul(question_embedding, answer_embedding.transpose(0, 1)).item()
    
    return similarity

# Example usage
question = "What is XLNet?"
answer = "XLNet is a new unsupervised language representation learning method based on a novel generalized permutation language modeling objective."

similarity_score = compute_similarity(question, answer)
print(f"Similarity score: {similarity_score}")
