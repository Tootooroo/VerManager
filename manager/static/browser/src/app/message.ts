export interface Message {
    type: string;
    content: { [index: string]: any };
}

export function message_check(msg: any): boolean {
    if (typeof msg == 'object') {
        if (typeof msg['type'] != 'undefined' ||
            typeof msg['content'] != 'undefined') {

            return true;
        }

        return false;
    }
}
