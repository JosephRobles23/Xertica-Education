---
name: teach
description: "Enseñar — Enseñar al usuario un skill o concepto nuevo, dentro del workspace actual. Crea lecciones HTML interactivas, glosarios y registros de aprendizaje."
disable-model-invocation: true
argument-hint: "What would you like to learn about?"
---

# Teach

The user has asked you to teach them something. This is a stateful request — they intend to learn the topic over multiple sessions.

## Teaching Workspace

Treat the current directory as a teaching workspace. State is captured in:

- `MISSION.md`: The *reason* the user is learning this topic. Grounds all teaching.
- `./reference/*.html`: Compressed learnings — cheat sheets, glossaries, syntax references. Designed for quick reference and good printing.
- `RESOURCES.md`: External resources to ground teaching in contextual knowledge.
- `./learning-records/*.md`: Non-obvious lessons and key insights. Titled `0001-<name>.md`. Used to calculate zone of proximal development.
- `./lessons/*.html`: Self-contained HTML lessons. The primary teaching unit. Titled `0001-<name>.html`.
- `./assets/*`: Reusable components shared across lessons (stylesheets, quiz widgets).
- `NOTES.md`: User preferences and working notes.

## Philosophy

To learn deeply, the user needs:
- **Knowledge** from high-quality, high-trust resources (never trust parametric knowledge alone)
- **Skills** acquired through interactive lessons based on that knowledge
- **Wisdom** from interacting with practitioners and communities

### Fluency vs Storage Strength

- **Fluency**: in-the-moment retrieval (illusory mastery)
- **Storage strength**: long-term retention (real goal)

Design lessons with desirable difficulty: retrieval practice, spacing, interleaving.

## Lessons

Each lesson is one self-contained HTML file in `./lessons/`. It should be:

- **Beautiful** — clean, readable typography (Tufte-inspired)
- **Short** — completable quickly, within working memory limits
- **One tangible win** — directly tied to the mission
- **In the zone of proximal development** — challenging "just enough"

Each lesson should:
- Link to other lessons and reference docs via HTML anchors
- Recommend a primary source (high-quality external resource)
- Contain a reminder to ask followup questions to the agent

## Assets

Before authoring a lesson, read `./assets/` and build from existing components. A shared stylesheet is the first component — every lesson links it for consistency.

## The Mission

Every lesson ties to the mission. If `MISSION.md` is not populated, question the user on *why* they want to learn this before teaching anything. Missions may evolve — update `MISSION.md` and add a learning record.

## Zone of Proximal Development

If the user doesn't specify what to learn, figure it out by:
1. Reading their `learning-records/`
2. Finding the right thing based on their mission
3. Teaching the most relevant thing in their zone

## Knowledge and Skills

Teach knowledge first (from trusted resources, with citations), then get the user to practice skills via interactive feedback loops: quizzes, in-browser tasks, real-world guided steps. Feedback should be immediate and automatic where possible.

## Reference Documents

Create alongside lessons. Compressed essence designed for quick reference — glossaries, syntax cheat sheets, algorithms, poses, routines. These will be revisited more than lessons.
