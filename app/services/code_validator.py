# services/code_validator.py
from logzero import logger
import ast
import re
from typing import Dict, List, Tuple
from app.schemas.code_converter import CodeConversionRequest, ProgrammingLanguage

class CodeValidatorService:
    # Language-specific comment patterns
    COMMENT_PATTERNS = {
        "python": (
            r"#.*$",  # Single line comments
            r'"""[\s\S]*?"""',  # Multi-line docstrings
            r"'''[\s\S]*?'''"  # Alternative multi-line docstrings
        ),
        "javascript": (
            r"//.*$",  # Single line comments
            r"/\*[\s\S]*?\*/",  # Multi-line comments
            r"/\*\*[\s\S]*?\*/"  # JSDoc comments
        ),
        "typescript": (
            r"//.*$",  # Single line comments
            r"/\*[\s\S]*?\*/",  # Multi-line comments
            r"/\*\*[\s\S]*?\*/"  # TSDoc comments
        ),
        "java": (
            r"//.*$",  # Single line comments
            r"/\*[\s\S]*?\*/",  # Multi-line comments
            r"/\*\*[\s\S]*?\*/"  # Javadoc comments
        ),
        "csharp": (
            r"//.*$",  # Single line comments
            r"/\*[\s\S]*?\*/",  # Multi-line comments
            r"///.*$"  # XML documentation comments
        ),
        "cpp": (
            r"//.*$",  # Single line comments
            r"/\*[\s\S]*?\*/",  # Multi-line comments
        ),
        "php": (
            r"#.*$",  # Shell-style comments
            r"//.*$",  # Single line comments
            r"/\*[\s\S]*?\*/",  # Multi-line comments
        ),
        "ruby": (
            r"#.*$",  # Single line comments
            r"=begin[\s\S]*?=end"  # Multi-line comments
        ),
        "go": (
            r"//.*$",  # Single line comments
            r"/\*[\s\S]*?\*/"  # Multi-line comments
        ),
        "rust": (
            r"//.*$",  # Single line comments
            r"/\*[\s\S]*?\*/",  # Multi-line comments
            r"///.*$"  # Documentation comments
        ),
        "swift": (
            r"//.*$",  # Single line comments
            r"/\*[\s\S]*?\*/",  # Multi-line comments
            r"///.*$"  # Documentation comments
        ),
        "kotlin": (
            r"//.*$",  # Single line comments
            r"/\*[\s\S]*?\*/",  # Multi-line comments
            r"/\*\*[\s\S]*?\*/"  # KDoc comments
        )
    }

    # Language-specific syntax validators
    @staticmethod
    def _python_validator(code: str) -> bool:
        try:
            ast.parse(code)
            return True
        except:
            return False


    # Add more language-specific validators
    SYNTAX_VALIDATORS = {
        "python": lambda code: CodeValidatorService._python_validator(code),
       
    }

    @staticmethod
    def _check_syntax(code: str, language: str) -> Tuple[bool, str]:
        """Check code syntax based on language"""
        try:
            if language in CodeValidatorService.SYNTAX_VALIDATORS:
                is_valid = CodeValidatorService.SYNTAX_VALIDATORS[language](code)
                return is_valid, "Syntax is valid" if is_valid else "Invalid syntax detected"
            
            # For languages without specific validators, perform basic structural checks
            return CodeValidatorService._general_syntax_check(code, language)
            
        except Exception as e:
            return False, f"Syntax error: {str(e)}"

    
    @staticmethod
    def _general_syntax_check(code: str, language: str) -> Tuple[bool, str]:
        """Perform general syntax checks for languages without specific validators"""
        issues = []
        
        # Check for basic structural issues
        if language in ["java", "csharp", "cpp", "kotlin"]:
            if not re.search(r"\bclass\b", code) and not re.search(r"\bpublic\b.*\bmain\b", code):
                issues.append("No class or main method found")
            if code.count('{') != code.count('}'):
                issues.append("Mismatched braces")
                
        elif language in ["go"]:
            if not re.search(r"\bfunc\b", code):
                issues.append("No function declarations found")
            if code.count('{') != code.count('}'):
                issues.append("Mismatched braces")
                
        elif language in ["rust"]:
            if not re.search(r"\bfn\b", code):
                issues.append("No function declarations found")
            if code.count('{') != code.count('}'):
                issues.append("Mismatched braces")
                
        elif language in ["swift"]:
            if not re.search(r"\bfunc\b", code) and not re.search(r"\bclass\b", code):
                issues.append("No function or class declarations found")
            
        elif language in ["php"]:
            if not re.search(r"<\?php", code):
                issues.append("Missing PHP opening tag")

        return len(issues) == 0, "Syntax appears valid" if len(issues) == 0 else f"Potential issues: {', '.join(issues)}"

    @staticmethod
    def _analyze_complexity(code: str) -> Dict:
        """Analyze code complexity"""
        complexity_metrics = {
            "lines_of_code": len(code.splitlines()),
            "characters": len(code),
            "empty_lines": len([line for line in code.splitlines() if not line.strip()]),
            "max_line_length": max(len(line) for line in code.splitlines()) if code.splitlines() else 0,
            "cyclomatic_complexity": CodeValidatorService._calculate_cyclomatic_complexity(code)
        }
        
        # Check if code might be too complex
        if complexity_metrics["lines_of_code"] > 1000:
            complexity_metrics["warning"] = "Code is quite long and might need to be split into smaller chunks"
        elif complexity_metrics["max_line_length"] > 100:
            complexity_metrics["warning"] = "Some lines are too long and might need reformatting"
        elif complexity_metrics["cyclomatic_complexity"] > 10:
            complexity_metrics["warning"] = "Code has high cyclomatic complexity, consider refactoring"
            
        return complexity_metrics

    @staticmethod
    def _extract_comments(code: str, language: str) -> List[str]:
        """Extract comments from code based on language patterns"""
        comments = []
        if language in CodeValidatorService.COMMENT_PATTERNS:
            for pattern in CodeValidatorService.COMMENT_PATTERNS[language]:
                comments.extend(re.findall(pattern, code, re.MULTILINE))
        return [comment.strip() for comment in comments if comment.strip()]
    

    @staticmethod
    def _calculate_cyclomatic_complexity(code: str) -> int:
        """Calculate cyclomatic complexity based on control flow statements"""
        # Count control flow statements
        control_patterns = [
            r'\bif\b', r'\belse\b', r'\bfor\b', r'\bwhile\b', r'\bcase\b',
            r'\bcatch\b', r'\b&&\b', r'\|\|'
        ]
        complexity = 1  # Base complexity
        for pattern in control_patterns:
            complexity += len(re.findall(pattern, code))
        return complexity
    @staticmethod
    def _check_potential_issues(code: str) -> List[str]:
        """Check for potential code issues"""
        issues = []
        
        # Security checks
        if re.search(r"password\s*=\s*['\"][^'\"]+['\"]", code, re.IGNORECASE):
            issues.append("Contains hardcoded password")
        
        if re.search(r"api[_-]?key\s*=\s*['\"][^'\"]+['\"]", code, re.IGNORECASE):
            issues.append("Contains hardcoded API key")

        # Performance checks
        if re.search(r"while\s*True|while\s*1", code):
            issues.append("Contains potential infinite loop")
        
        if re.search(r"['\"][^'\"]{1000,}['\"]", code):
            issues.append("Contains very large string literals")

        # Quality checks
        if re.search(r"\btodo\b|\bfixme\b", code, re.IGNORECASE):
            issues.append("Contains TODO or FIXME comments")
            
        if re.search(r"print\s*\(|console\.log\s*\(|System\.out\.print", code):
            issues.append("Contains debug print statements")

        return issues

    @staticmethod
    def validate_code(request: CodeConversionRequest) -> Dict:
        """Comprehensive code validation"""
        try:
            logger.info(f"Starting code validation for {request.source_language} code")
            
            # Basic checks
            if not request.source_code.strip():
                raise ValueError("Source code is empty")

            # Syntax validation
            syntax_valid, syntax_message = CodeValidatorService._check_syntax(
                request.source_code,
                request.source_language.value
            )

            # Extract and analyze comments
            comments = CodeValidatorService._extract_comments(
                request.source_code,
                request.source_language.value
            )

            # Analyze code complexity
            complexity_metrics = CodeValidatorService._analyze_complexity(request.source_code)

            # Check for potential issues
            issues = CodeValidatorService._check_potential_issues(request.source_code)

            validation_result = {
                "is_valid": syntax_valid,
                "syntax_message": syntax_message,
                "source_language": request.source_language,
                "target_language": request.target_language,
                "complexity_metrics": complexity_metrics,
                "comments_analysis": {
                    "has_comments": bool(comments),
                    "comment_count": len(comments),
                    "comments": comments[:5] if comments else []  # Show first 5 comments
                },
                "potential_issues": issues,
                "recommendations": []
            }

            # Add recommendations based on analysis
            if not comments and complexity_metrics["lines_of_code"] > 50:
                validation_result["recommendations"].append(
                    "Consider adding comments to improve code readability"
                )
            if issues:
                validation_result["recommendations"].append(
                    "Address potential code issues before conversion"
                )
            if complexity_metrics.get("warning"):
                validation_result["recommendations"].append(
                    complexity_metrics["warning"]
                )

            logger.info("Code validation completed successfully")
            return validation_result

        except Exception as e:
            logger.error(f"Code validation failed: {str(e)}")
            raise ValueError(f"Code validation failed: {str(e)}")