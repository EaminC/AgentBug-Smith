import os
import tempfile

def test_workflow_cache_restart_functionality():
    """Test WorkflowCache for restarting previous sessions (Issue #121)."""
    # This import should fail before the patch and succeed after
    from mle.utils import WorkflowCache
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Setup: Create project.yml in temp directory
        config_path = os.path.join(tmpdir, 'project.yml')
        with open(config_path, 'w') as f:
            f.write('{}')
        
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            
            # Test 1: Create cache and verify initial state
            cache = WorkflowCache(tmpdir)
            assert cache.is_empty(), "New cache should be empty"
            
            # Test 2: Store data in step 1 (simulating first step of workflow)
            with cache(step=1, name="data collection") as ca:
                ca.store("dataset", "user_data.csv")
                ca.store("config", {"type": "csv"})
            
            # Test 3: Verify cache is not empty and tracks current step
            assert not cache.is_empty(), "Cache should contain data after storing"
            assert cache.current_step() == 1, "Current step should be 1"
            
            # Test 4: Simulate session restart by creating new cache instance
            # This is the key functionality for Issue #121 - restarting previous session
            cache2 = WorkflowCache(tmpdir)
            assert not cache2.is_empty(), "Cache should persist for session restart"
            assert cache2.current_step() == 1, "Step should persist across cache instances"
            
            # Test 5: Resume data from previous session
            with cache2(step=1, name="data collection") as ca:
                dataset = ca.resume("dataset")
                config = ca.resume("config")
                assert dataset == "user_data.csv", "Should resume dataset from previous session"
                assert config == {"type": "csv"}, "Should resume config from previous session"
                nonexistent = ca.resume("nonexistent")
                assert nonexistent is None, "Non-existent keys should return None"
            
            # Test 6: Add more steps and verify step tracking
            with cache(step=2, name="model training") as ca:
                ca.store("model", "random_forest")
            
            assert cache.current_step() == 2, "Current step should update to 2"
            
            # Test 7: Test step removal (for reverting to previous step)
            cache.remove(2)
            assert cache.current_step() == 1, "Current step should revert to 1 after removal"
            
            # Verify step 2 data is gone
            assert 2 not in cache.cache, "Step 2 should be removed from cache"
            
            # Test 8: Verify string representation contains step info
            cache_str = str(cache)
            assert "[1]" in cache_str, "String representation should show step number"
            assert "data collection" in cache_str, "String representation should show step name"
            
        finally:
            os.chdir(original_cwd)
