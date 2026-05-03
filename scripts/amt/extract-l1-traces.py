#!/usr/bin/env python3
"""Extract key data from L1 trace files for the cross-agent report."""
import json
import os
import sys

BASE = "data/mode-a-shard-a/track-a/runs/97507afa-7b9e-4064-9852-48f55c238e3c/cases"

CASES = {
    "L1_task4_text": "ecommerce_admin_individual_4_0_1_L1",
    "L1_task4_cua": "ecommerce_admin_individual_4_2_1_L1",
    "L1_task4_som": "ecommerce_admin_individual_4_1_1_L1",
    "L1_task29_text": "reddit_individual_29_0_1_L1",
    "L1_task29_cua": "reddit_individual_29_2_1_L1",
    "L1_task308_text": "gitlab_individual_308_0_1_L1",
    "L1_task23_text": "ecommerce_individual_23_0_1_L1",
    "L6_task4_text": "ecommerce_admin_individual_4_0_1_L6",
}

for name, case_dir in CASES.items():
    path = os.path.join(BASE, case_dir)
    trace_path = os.path.join(path, "trace-attempt-1.json")
    sr_path = os.path.join(path, "scan-result.json")
    
    print(f"\n{'='*80}")
    print(f"CASE: {name} ({case_dir})")
    print(f"{'='*80}")
    
    # Scan result
    if os.path.exists(sr_path):
        with open(sr_path) as f:
            sr = json.load(f)
        lc = sr.get("tier2", {}).get("landmarkCoverage", "N/A")
        cs = sr.get("compositeScore", {}).get("compositeScore", "N/A")
        a11y_tree = sr.get("a11yTreeSnapshot", {}).get("ariaTree", "")
        print(f"\n--- SCAN RESULT ---")
        print(f"landmarkCoverage: {lc}")
        print(f"compositeScore: {cs}")
        # First 20 lines of a11y tree
        if a11y_tree:
            lines = a11y_tree.split("\n")
            print(f"\n--- A11Y TREE (first 25 lines of {len(lines)} total) ---")
            for line in lines[:25]:
                print(line)
    
    # Trace
    if os.path.exists(trace_path):
        with open(trace_path) as f:
            trace = json.load(f)
        
        print(f"\n--- TRACE SUMMARY ---")
        # Top-level fields
        reward = trace.get("reward", "N/A")
        success = trace.get("success", "N/A")
        n_steps = trace.get("n_steps", len(trace.get("steps", [])))
        total_tokens = trace.get("total_tokens", "N/A")
        task_intent = trace.get("task_intent", trace.get("intent", "N/A"))
        
        print(f"reward: {reward}")
        print(f"success: {success}")
        print(f"n_steps: {n_steps}")
        print(f"total_tokens: {total_tokens}")
        print(f"task_intent: {task_intent}")
        
        steps = trace.get("steps", [])
        if not steps:
            # Try alternate structure
            steps = trace.get("trace", [])
        
        if steps:
            # Step 0 observation
            step0 = steps[0]
            obs = step0.get("observation", step0.get("obs", ""))
            if isinstance(obs, dict):
                obs_text = obs.get("text", obs.get("a11y_tree", str(obs)[:500]))
            else:
                obs_text = str(obs)
            
            # First 25 lines of step 0 observation
            obs_lines = obs_text.split("\n")
            print(f"\n--- STEP 0 OBSERVATION (first 25 of {len(obs_lines)} lines) ---")
            for line in obs_lines[:25]:
                print(line)
            
            # Check for landmarks in step 0
            landmarks = ["banner", "navigation", "main", "contentinfo", "complementary", "region"]
            found = [lm for lm in landmarks if lm in obs_text.lower()]
            missing = [lm for lm in landmarks if lm not in obs_text.lower()]
            print(f"\n--- LANDMARKS IN STEP 0 ---")
            print(f"Found: {found}")
            print(f"Missing: {missing}")
            
            # Agent reasoning at key steps (first 3 steps)
            for i, step in enumerate(steps[:5]):
                reasoning = step.get("reasoning", step.get("think", step.get("thought", "")))
                action = step.get("action", step.get("act", ""))
                if isinstance(action, dict):
                    action = json.dumps(action)[:200]
                else:
                    action = str(action)[:200]
                
                if reasoning:
                    print(f"\n--- STEP {i} REASONING ---")
                    print(str(reasoning)[:500])
                print(f"--- STEP {i} ACTION ---")
                print(action[:200])
        else:
            print("NO STEPS FOUND in trace")
            # Print top-level keys
            print(f"Top-level keys: {list(trace.keys())}")
    else:
        print("NO trace-attempt-1.json")
