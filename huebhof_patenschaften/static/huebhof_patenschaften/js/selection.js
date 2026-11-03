// Like the subscription type selection of juntagrico (js/initCreateSubscription.js),
// but instead of a "no selection" switch, the submit button tells what happens.
$(function () {
    let quantities = $('input.sponsorship-quantity')
    let submit = $('button.sponsorship-submit')

    function total_selected() {
        let amount = 0
        quantities.each(function () {
            amount += parseInt(this.value) || 0
        })
        return amount
    }

    quantities.change(function () {
        // highlight card and show the choice of the sponsorship year, if value != 0
        let selected = (parseInt(this.value) || 0) !== 0
        $(this).closest('.card').toggleClass('bg-primary', selected)
            .find('.sponsorship-year-choice').toggleClass('d-none', !selected)
        let total = total_selected()
        if (total === 0) {
            submit.text(submit.data('label-none'))
        } else if (total === 1) {
            submit.text(submit.data('label-one'))
        } else {
            submit.text(submit.data('label-many').replace('__count__', total))
        }
    }).change()

    if ($().inputSpinner) {
        quantities.inputSpinner({groupClass: 'subscription-order'})
    }
})
