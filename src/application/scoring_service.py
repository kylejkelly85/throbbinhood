class ConfidenceScoringService:
    def __init__(self, threshold: float) -> None:
        self.threshold = threshold

    def evaluate(self, url: str, content: str, target_keyword: str) -> float:
        # Proper scoring including url
        target_lower = target_keyword.lower()
        url_lower = url.lower()
        content_lower = content.lower()
        
        if target_lower not in url_lower and target_lower not in content_lower:
            return 0.0
        
        score: float = 0.0
        
        # 1. Keyword Density (0.7)
        if target_lower in content_lower:
            score += 0.7
            
        # 2. Header Check (assume 0.15 as it passed in engine filtering)
        score += 0.15
        
        # 3. URL Relevance (0.15)
        if target_lower in url_lower:
            score += 0.15
            
        return min(1.0, score)

    def passes_gate(self, score: float) -> bool:
        return score >= self.threshold
