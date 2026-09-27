<file>colbert_live/db/astra.py</file>
<original>class AstraDB:
    def __init__(self, ...):
        # existing constructor code
        ...
</original>
<patched>class AstraDB:
    def __init__(self, ..., verbose=False):
        # existing constructor code
        self.verbose = verbose
        if self.verbose:
            print(f"AstraDB initialized with verbose={self.verbose}")
        ...
</patched>
</file>

<file>colbert_live/db/astra.py</file>
<original>    def some_method(self, ...):
        # method logic
        ...
</original>
<patched>    def some_method(self, ...):
        if self.verbose:
            print(f"Entering some_method with args: ...")
        # method logic
        ...
        if self.verbose:
            print("Exiting some_method")        
</patched>
</file>

<file>colbert_live/db/astra.py</file>
<original>    def another_method(self, ...):
        # method logic
        ...
</original>
<patched>    def another_method(self, ...):
        if self.verbose:
            print(f"another_method called with args: ...")
        # method logic
        ...
</patched>
</file>