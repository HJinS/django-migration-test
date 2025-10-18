import sys
import timeit
import uuid

# test data size
DATA_SIZE = 1_000_000

# initialize data structure
# assume that there is no duplicated items.
# use uuid to generated unique string.
my_list = [str(uuid.uuid4()) for _ in range(DATA_SIZE)]
my_set = set([str(uuid.uuid4()) for _ in range(DATA_SIZE)])

# take memory usage using `sys.getsizeof`
list_memory_byte = sys.getsizeof(my_list)
set_memory_byte = sys.getsizeof(my_set)

print("--- 💾 compare memory usage ---")
print(f"total count: {DATA_SIZE:,}")
print(f"List memory usage: {list_memory_byte:,} bytes")
print(f"Set  memory usage: {set_memory_byte:,} bytes")

# mesaure time to iterate each data structure using timeit
ITERATIONS = 100

list_iteration_time = timeit.timeit(
    stmt='for item in my_list: print(item, end="\\r")',
    globals=globals(),
    number=ITERATIONS
)

set_iteration_time = timeit.timeit(
    stmt='for item in my_set: print(item, end="\\r")',
    globals=globals(),
    number=ITERATIONS
)

print("--- ⏱️ Iteration Time Compare ---")
print(f"Total iteration count: {ITERATIONS}")
print(f"List iteration time: {list_iteration_time:.6f} s")
print(f"Set  iteration time: {set_iteration_time:.6f} s")
