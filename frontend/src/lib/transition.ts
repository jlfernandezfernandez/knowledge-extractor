export type Direction = "forward" | "back";

/**
 * Move the review to another step.
 *
 * The direction is written to the document so the CSS can send the outgoing
 * step out the way the incoming one arrives — enter and exit along the same
 * path, which is what makes "back" read as undoing rather than as a new
 * screen. Browsers without View Transitions get an instant swap.
 */
export function stepTo(direction: Direction, update: () => void) {
  document.documentElement.dataset.direction = direction;
  if (!document.startViewTransition) return update();
  document.startViewTransition(update);
}
