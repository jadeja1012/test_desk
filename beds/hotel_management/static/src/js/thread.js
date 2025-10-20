import { Thread } from "@mail/core/common/thread_model";
import { patch } from "@web/core/utils/patch";
import { AND, Record } from "@mail/core/common/record";

patch(Thread.prototype, {
    setup() {
        super.setup();
        this.suggestedRecipients = []
    },

})