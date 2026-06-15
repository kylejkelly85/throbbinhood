class ConfidenceScoringService:
    def __init__(self, threshold: float) -> None:
        self.threshold = threshold

    def evaluate(self, title: str, content: str) -> float:
        # Business logic for weighting the evaluation
        score: float = 0.5
        title_lower = title.lower()
        content_lower = content.lower()
        
        if "data" in title_lower or "data" in content_lower:
            score += 0.3
        
        if len(content_lower) > 300:
            score += 0.2
            
        return min(1.0, score)
    
    def passes_gate(self, score: float) -> bool:
        return score >= self.threshold
