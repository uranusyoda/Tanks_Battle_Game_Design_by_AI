// Keyboard / pointer input. Produces intents only; the game decides what they
// mean (and the rules decide whether they are legal).

export function createInput(canvas) {
  const keys = Object.create(null);
  const mouseNdc = { x: 0, y: 0 };
  let mouseDown = false;
  const handlers = new Map();

  const onKeyDown = (event) => {
    if (event.code === 'Space') event.preventDefault();
    keys[event.code] = true;
    const handler = handlers.get(event.code);
    if (handler) handler(event);
  };
  const onKeyUp = (event) => {
    keys[event.code] = false;
  };
  const onMove = (event) => {
    mouseNdc.x = (event.clientX / innerWidth) * 2 - 1;
    mouseNdc.y = -(event.clientY / innerHeight) * 2 + 1;
  };
  const onDown = (event) => {
    if (event.button === 0 && event.target === canvas) mouseDown = true;
  };
  const onUp = () => {
    mouseDown = false;
  };
  const onContext = (event) => {
    if (event.target === canvas) event.preventDefault();
  };

  addEventListener('keydown', onKeyDown);
  addEventListener('keyup', onKeyUp);
  addEventListener('mousemove', onMove);
  addEventListener('mousedown', onDown);
  addEventListener('mouseup', onUp);
  addEventListener('contextmenu', onContext);

  return {
    keys,
    mouseNdc,
    isMouseDown: () => mouseDown,
    onKey(code, fn) {
      handlers.set(code, fn);
    },
    dispose() {
      removeEventListener('keydown', onKeyDown);
      removeEventListener('keyup', onKeyUp);
      removeEventListener('mousemove', onMove);
      removeEventListener('mousedown', onDown);
      removeEventListener('mouseup', onUp);
      removeEventListener('contextmenu', onContext);
    },
  };
}
