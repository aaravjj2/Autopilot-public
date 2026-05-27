from db.seed import seed_all

if __name__ == "__main__":
    counts = seed_all()
    print("Seeded DB row counts:")
    print(f"wc_matches: {counts.get('wc_matches', 0)}")
    print(f"international_results: {counts.get('international_results', 0)}")
    print(f"fixtures_2026: {counts.get('fixtures_2026', 0)}")
