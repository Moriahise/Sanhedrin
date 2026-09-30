# Modernization work branch

The autonomous-library modernization is being restored and verified after automatic scratch-workspace maintenance. This branch is isolated from main and production.

Target: preserve all 63,051 public IDs, restore missing source records, replace the responsa.json runtime monolith with a versioned catalogue and full-text index, and replace manual extension exports with transactional collectors and durable recovery snapshots.

Previous full-data audit: 64,264 entries including 17 documents; 246/246 first-2026 Yeshiva import records and 260,640 historical aliases retained. These results must be reproduced on the committed implementation before release.
