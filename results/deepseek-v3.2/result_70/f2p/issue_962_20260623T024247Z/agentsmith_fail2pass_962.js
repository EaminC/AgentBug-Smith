const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Helper to get conversations directory
function getConversationsDir() {
  const home = process.env.HOME || process.env.USERPROFILE;
  return path.join(home, '.openinterpreter', 'conversations');
}

// Helper to create a dummy conversation file
function createDummyConversation() {
  const convDir = getConversationsDir();
  if (!fs.existsSync(convDir)) {
    fs.mkdirSync(convDir, { recursive: true });
  }
  const fileName = `test_conv_${Date.now()}.json`;
  const filePath = path.join(convDir, fileName);
  // Simulate the new streaming format after fix: each chunk has "type" and "content"
  const messages = [
    { type: 'message', content: 'Hello, how are you?' },
    { type: 'code', format: 'python', content: 'print("Hello")', active_line: 1 },
    { type: 'console', content: 'Hello' },
  ];
  fs.writeFileSync(filePath, JSON.stringify(messages));
  return filePath;
}

// Helper to delete dummy conversation
function cleanupDummyConversation(filePath) {
  if (fs.existsSync(filePath)) {
    fs.unlinkSync(filePath);
  }
}

// Main test
function testConversationRestoration() {
  // 1. Create a dummy conversation file
  const convPath = createDummyConversation();
  console.log('Created dummy conversation at:', convPath);

  try {
    // 2. Try to import conversation_navigator and render_past_conversation
    // Since they are Python modules, we cannot directly require them in JS.
    // Instead, we'll simulate the bug by checking the actual Python files.
    // We'll read the Python source and see if the buggy pattern exists.
    const repoRoot = path.resolve(__dirname, '..');
    const navPath = path.join(repoRoot, 'interpreter', 'terminal_interface', 'conversation_navigator.py');
    const renderPath = path.join(repoRoot, 'interpreter', 'terminal_interface', 'render_past_conversation.py');

    if (!fs.existsSync(navPath) || !fs.existsSync(renderPath)) {
      throw new Error('Python source files not found');
    }

    const navContent = fs.readFileSync(navPath, 'utf8');
    const renderContent = fs.readFileSync(renderPath, 'utf8');

    // 3. Check for buggy patterns
    // In buggy version, conversation_navigator prints the "not working" message.
    const hasBuggyMessage = navContent.includes('This feature is not working as of 0.2.0');
    // In buggy version, render_past_conversation uses chunk["message"] instead of chunk["content"]
    const hasBuggyKeyMessage = renderContent.includes('chunk["message"]');
    const hasBuggyKeyCode = renderContent.includes('"code" in chunk') && renderContent.includes('"language" in chunk');
    const hasBuggyKeyOutput = renderContent.includes('"output" in chunk');

    // 4. Determine expected behavior based on buggy vs fixed
    // If buggy patterns exist, the test should fail (exit code non-zero).
    // After fix, patterns should be gone, test should pass (exit code zero).
    // We'll use assertions that will throw if buggy patterns are present.
    if (hasBuggyMessage) {
      throw new Error('Buggy message still present in conversation_navigator.py');
    }
    if (hasBuggyKeyMessage) {
      throw new Error('Buggy key "message" still present in render_past_conversation.py');
    }
    if (hasBuggyKeyCode) {
      throw new Error('Buggy keys "code"/"language" still present in render_past_conversation.py');
    }
    if (hasBuggyKeyOutput) {
      throw new Error('Buggy key "output" still present in render_past_conversation.py');
    }

    // 5. Additionally, verify the fixed patterns are present
    // After fix, render_past_conversation should use chunk["content"] and chunk["type"]
    const hasFixedContent = renderContent.includes('chunk["content"]');
    const hasFixedType = renderContent.includes('chunk["type"]');
    if (!hasFixedContent || !hasFixedType) {
      throw new Error('Fixed patterns not found in render_past_conversation.py');
    }

    console.log('All checks passed: conversation restoration code appears fixed.');
  } finally {
    // Cleanup
    cleanupDummyConversation(convPath);
  }
}

// Run the test
try {
  testConversationRestoration();
  console.log('Test passed');
} catch (error) {
  console.error('Test failed:', error.message);
  process.exit(1);
}
