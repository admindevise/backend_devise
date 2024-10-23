const action_selection_page = document.getElementById('_action_selection_page');
const action_select = document.getElementById('_action_select');
const action_file_format = document.getElementById('_action_file_format');
const action_confirm_button = document.getElementById('_action_confirm_button');
const action_select_all = document.getElementById('_action_select_all');
const action_select_clear = document.getElementById('_action_select_clear');
const selected_all_elements = document.getElementById('_selected_all_elements');

const checkboxes = document.querySelectorAll('.form-checked-input');
const span_counts = document.getElementById('_count_selected_items');

let selected_actions_elements = 0;
let total_actions_elements = Number(span_counts.getAttribute('total-elements'));


window.addEventListener('DOMContentLoaded', (event) => {
  updateCountSelectedElements();
});

if(action_selection_page){
  action_selection_page.addEventListener('click', (e) => {
    status_checked = e.target.checked;
    checkboxes.forEach((checkbox, i) => {
      checkbox.checked = status_checked;
    });
    if (status_checked) {
      selected_actions_elements = checkboxes.length;
      action_select_all.style.display = 'block';
    }else{
      selected_actions_elements = 0;
      action_select_all.style.display = 'none';
      action_select_clear.style.display = 'none';
    }
    document.getElementById('_action_error_selection').style.display = 'none';
    updateCountSelectedElements();
  });
}

if (action_select){
  action_select.addEventListener('change', (e) => {
    value = e.target.value;
    let input_action = document.getElementById('_action');
    input_action.value = value;
    if (value == 'export_admin_action') {
      action_file_format.classList.add('active');
    }else{
      action_file_format.classList.remove('active');
      select_action_file_format = action_file_format.children[0];
      select_action_file_format.value = '';
    }
    if (value != '') {
      document.getElementById('_action_error_action').style.display = 'none';
    }
  });
}

if (action_file_format) {
  action_file_format.addEventListener('change', (e) => {
    value = e.target.value;
    let input_file_format = document.getElementById('_format');
    input_file_format.value = value;
    if (value != '') {
      document.getElementById('_action_error_action').style.display = 'none';
    }
  });
}

if (action_confirm_button) {
  action_confirm_button.addEventListener('click', (e) => {
    console.log("Click confirm button");
    action = action_select.value;
    model = document.querySelector("input[name='model_action']").value;
    if (selected_actions_elements == 0){
      document.getElementById('_action_error_selection').style.display = 'block';
    }else {
      document.getElementById('_action_error_selection').style.display = 'none';
    }
    if(action != ''){
      if (selected_actions_elements > 0) {
        if(action == 'export_admin_to_pdf'){
          if (model == 'user' ) {
            const form = document.getElementById('action-list-form');
            form.submit();
          }else if(model == 'transaction'){
            const form = document.getElementById('action-list-form');
            form.submit();
          }
        }else{
          if (action_file_format.children[0].value != '') {
            const form = document.getElementById('action-list-form');
            form.submit();
          }else{
            document.getElementById('_action_error_action').style.display = 'block';
          }
        }
      }
    }else{
      document.getElementById('_action_error_action').style.display = 'block';
    }
  });
}

checkboxes.forEach((checkbox, i) => {
  checkbox.addEventListener('change', () => {
    if (checkbox.checked){
      selected_actions_elements += 1;
    }else{
      action_selection_page.checked = false;
      selected_actions_elements -= 1;
    }
    document.getElementById('_action_error_selection').style.display = 'none';
    updateCountSelectedElements();
  });
});

if (action_select_all) {
  action_select_all.addEventListener('click', (e) => {
    selected_all_elements.value = 1;
    updateCountSelectedElements(all=true);
    action_select_clear.style.display = 'block';
    action_select_all.style.display = 'none';
  });
}

if (action_select_clear) {
  action_select_clear.addEventListener('click', (e) => {
    selected_all_elements.value = 0;
    updateCountSelectedElements();
    action_select_all.style.display = 'block';
    action_select_clear.style.display = 'none';
  });
}

function updateCountSelectedElements(all=false) {
  console.log('actualizando');
  console.log(all);
  if (all == true){
    span_counts.textContent = `${total_actions_elements} of ${total_actions_elements} Selected `;
  }else{
    span_counts.textContent = `${selected_actions_elements} of ${checkboxes.length} Selected `;
  }
}
