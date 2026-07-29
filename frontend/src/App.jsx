import {Button, Card} from "@heroui/react";

export default function App() {
    return (
        <main className="min-h-screen bg-background p-8 text-foreground">
            <Card className="mx-auto max-w-xl">
                <Card.Header>
                    <Card.Title>ServicePath</Card.Title>
                    <Card.Description>
                        Five-layer website diagnostics
                    </Card.Description>
                </Card.Header>
                <Card.Content>
                    <p>The HeroUI frontend is ready.</p>
                </Card.Content>
                <Card.Footer>
                    <Button variant="primary">Start diagnosis</Button>
                </Card.Footer>
            </Card>
        </main>
    );
}
