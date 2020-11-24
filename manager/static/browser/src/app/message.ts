export interface Message {
    msg_type: string;
    content: { [index: string]: any };
}

export function message_parse(msg_str: string): Message | null {
    let message: Message;

    try {
        message = JSON.parse(msg_str);
    } catch (error) {
        /**
         * Treat the message is invalid just return null.
         */
        if (error instanceof SyntaxError) {
            return null;
        }

        // Another exception should be throw to upper.
        throw error;
    }

    return message;
}
