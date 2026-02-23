"""Quick test of the new search system"""
import sys
sys.path.insert(0, '.')

from scraper import search_bollyflix

# Test 1: Popular search
print("=" * 60)
print("TEST 1: 'avengers' (should get 20+ results)")
print("=" * 60)
results = search_bollyflix("avengers", limit=20)
print(f"\nTotal results: {len(results)}")
for i, r in enumerate(results):
    print(f"  [{i+1}] {r['clean_title'][:50]} ({r['year']}) [{r['content_type']}]")

print()

# Test 2: Less popular search
print("=" * 60)
print("TEST 2: 'pushpa' (should find results)")
print("=" * 60)
results2 = search_bollyflix("pushpa", limit=20)
print(f"\nTotal results: {len(results2)}")
for i, r in enumerate(results2[:5]):
    print(f"  [{i+1}] {r['clean_title'][:50]} ({r['year']}) [{r['content_type']}]")

print("\n✅ Test complete!")
