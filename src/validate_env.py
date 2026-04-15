import sys

def check_libraries():
    required_libs = ["faker", "sklearn", "mlflow", "pandas"]
    missing_libs = []

    print("--- Environment Validation Start ---")
    for lib in required_libs:
        try:
            module = __import__(lib)
            # Handle sklearn naming quirk
            version = getattr(module, "__version__", "unknown")
            print(f"✅ {lib} is installed (Version: {version})")
        except ImportError:
            print(f"❌ {lib} is MISSING")
            missing_libs.append(lib)

    if missing_libs:
        print(f"\nFATAL: Missing libraries: {missing_libs}")
        print("Please install them on cluster 0409-125523-8dr7mmxn before re-running.")
        sys.exit(1) # Exit with error code to stop the pipeline
    
    print("--- Environment Validation Passed ---")

if __name__ == "__main__":
    check_libraries()