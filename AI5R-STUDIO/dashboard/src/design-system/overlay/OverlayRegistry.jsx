import Modal from "./modal/Modal";
import Drawer from "./drawer/Drawer";
import Dialog from "./dialog/Dialog";
import Popover from "./popover/Popover";
import Tooltip from "./tooltip/Tooltip";
import ContextMenu from "./context-menu/ContextMenu";
import Loading from "./loading/Loading";
import Wizard from "./wizard/Wizard";

const registry = new Map();

function register(type, component) {
    registry.set(type, { type, component });
}

function unregister(type) {
    registry.delete(type);
}

function has(type) {
    return registry.has(type);
}

function get(type) {
    return registry.get(type) ?? null;
}

register("modal", Modal);
register("drawer", Drawer);
register("dialog", Dialog);
register("popover", Popover);
register("tooltip", Tooltip);
register("context-menu", ContextMenu);
register("loading", Loading);
register("wizard", Wizard);

export default { register, unregister, has, get };
