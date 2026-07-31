export default function Spinner({size = "md"}) {
    return <span aria-hidden="true" className={`spinner spinner-${size}`} />;
}
