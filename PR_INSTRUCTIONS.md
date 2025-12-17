# Pull Request Instructions

## 1. Set up Remote Repository (First time only)

```bash
# Create a new repository on GitHub first, then:
git remote add origin https://github.com/YOUR_USERNAME/AutoSolve.git
git branch -M main
git push -u origin main
```

## 2. Create a Feature Branch

```bash
git checkout -b feature/fix-ocr-detection
```

## 3. Make Your Changes
- Your changes are already committed to the feature branch

## 4. Push to Remote

```bash
git push origin feature/fix-ocr-detection
```

## 5. Create Pull Request using GitHub CLI

```bash
gh pr create --title "fix(core): resolve OCR detection and screen capture issues" --body "$(cat <<'EOF'
## Summary
This PR fixes critical issues preventing the AutoSolve application from detecting captchas and trigger text.

## 🐛 Bug Fixes
- **Fixed Screen Capture Bug**: Resolved region capture not actually capturing images
- **Improved OCR Detection**: Fixed aggressive preprocessing that converted images to binary
- **Optimized Performance**: Implemented optimized region capture for faster OCR
- **Lowered OCR Confidence Threshold**: Changed from 0.7 to 0.5 for better detection

## ✅ Improvements
- Removed verbose logging (only ERROR level in console)
- Added status display every 10 seconds
- Optimized codebase for CPU performance
- Computer name now displayed in monitoring status

## 🧪 Test Plan
- [x] OCR detection test with "Live will end in..." text
- [x] Screen capture with optimized regions
- [x] Status display every 10 seconds
- [ ] Test with real jigsaw captchas
- [ ] Verify 24/7 monitoring stability

## 📋 Screenshots
- Test OCR detection successfully recognizes trigger text
- Application shows monitoring status with computer name
- Optimized region capture improves performance

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

## 6. Alternative: Create PR on GitHub
1. Visit https://github.com/YOUR_USERNAME/AutoSolve
2. Click "Compare & pull request"
3. Fill in the PR details using the content above
4. Create the pull request

## 7. Review Process
- Request code review from team members
- Address any review comments
- Merge after approval

## Notes
- Ensure you have write access to the repository
- The PR description includes all relevant changes and testing performed
- All tests should pass before merging